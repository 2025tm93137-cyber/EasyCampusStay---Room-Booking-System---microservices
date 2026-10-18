<?php
declare(strict_types=1);
namespace CampusStay;

const SERVICE_HOME = __DIR__ . '/..';

final class BusinessError extends \RuntimeException {
    public function __construct(public int $status, public string $errorCode, string $message, public mixed $details = null) {
        parent::__construct($message);
    }
    public function body(): array {
        return ['error'=>['code'=>$this->errorCode,'message'=>$this->getMessage(),'details'=>$this->details]];
    }
}

final class OperationBusy extends \RuntimeException {}

function configuration(): array {
    static $values = null;
    if ($values !== null) return $values;
    $values = [];
    $file = SERVICE_HOME . '/.env';
    foreach (is_file($file) ? file($file, FILE_IGNORE_NEW_LINES) : [] as $line) {
        $line = trim($line);
        if ($line === '' || str_starts_with($line, '#') || !str_contains($line, '=')) continue;
        [$key,$raw] = explode('=', $line, 2);
        $raw = trim($raw);
        $decoded = str_starts_with($raw, '"') ? json_decode($raw, true, 512, JSON_THROW_ON_ERROR) : $raw;
        $values[trim($key)] = (string)$decoded;
    }
    return $values;
}

function setting(string $key, ?string $default=null): ?string {
    $value = getenv($key);
    return $value !== false ? $value : (configuration()[$key] ?? $default);
}

function service_name(): string { return basename(realpath(SERVICE_HOME)); }

function uuid4(): string {
    $bytes=random_bytes(16);
    $bytes[6]=chr((ord($bytes[6]) & 15) | 64);
    $bytes[8]=chr((ord($bytes[8]) & 63) | 128);
    $hex=bin2hex($bytes);
    return substr($hex,0,8).'-'.substr($hex,8,4).'-'.substr($hex,12,4).'-'.substr($hex,16,4).'-'.substr($hex,20,12);
}

function log_event(string $event, string $cid='', array $fields=[]): void {
    $folder=SERVICE_HOME.'/logs';
    if (!is_dir($folder)) mkdir($folder,0700,true);
    $record=array_merge(['timestamp'=>gmdate('Y-m-d\TH:i:s\Z'),'service'=>service_name(),
                         'event'=>$event,'correlation_id'=>$cid],$fields);
    file_put_contents($folder.'/events.jsonl',json_encode($record,JSON_UNESCAPED_SLASHES|JSON_UNESCAPED_UNICODE|JSON_THROW_ON_ERROR)."\n",FILE_APPEND|LOCK_EX);
}

function json_text(mixed $value): string {
    return json_encode($value,JSON_UNESCAPED_SLASHES|JSON_UNESCAPED_UNICODE|JSON_THROW_ON_ERROR);
}

function canonical(mixed $value): mixed {
    if (!is_array($value)) return $value;
    if ($value!==[] && array_keys($value)!==range(0,count($value)-1)) ksort($value,SORT_STRING);
    foreach ($value as $key=>$item) $value[$key]=canonical($item);
    return $value;
}

final class Database {
    public \PDO $pdo;
    private array $locks=[];
    public function __construct() {
        foreach (['DB_NAME','DB_USER','DB_PASSWORD'] as $key) {
            if (setting($key)===null) throw new \RuntimeException('Configure this service .env first.');
        }
        $dsn='mysql:host='.setting('DB_HOST','127.0.0.1').';port='.setting('DB_PORT','3306').
             ';dbname='.setting('DB_NAME').';charset=utf8mb4';
        $this->pdo=new \PDO($dsn,setting('DB_USER'),setting('DB_PASSWORD'),[
            \PDO::ATTR_ERRMODE=>\PDO::ERRMODE_EXCEPTION,\PDO::ATTR_DEFAULT_FETCH_MODE=>\PDO::FETCH_ASSOC,
            \PDO::ATTR_EMULATE_PREPARES=>false,\PDO::ATTR_STRINGIFY_FETCHES=>false,
            \PDO::ATTR_TIMEOUT=>(int)setting('DB_CONNECT_TIMEOUT_SECONDS','5')]);
        $this->execute('SET SESSION TRANSACTION ISOLATION LEVEL READ COMMITTED');
        $this->execute("SET time_zone='+00:00'");
    }
    public function execute(string $sql,array $parameters=[]): \PDOStatement {
        $statement=$this->pdo->prepare($sql);
        $statement->execute($parameters);
        return $statement;
    }
    public function one(string $sql,array $parameters=[]): ?array {
        $row=$this->execute($sql,$parameters)->fetch();
        return $row===false ? null : $row;
    }
    public function lock(string $name,int $timeout=15): void {
        $token=hash('sha256',setting('DB_NAME').':'.$name);
        $row=$this->one('SELECT GET_LOCK(?,?) AS acquired',[$token,$timeout]);
        if ((int)$row['acquired']!==1) throw new OperationBusy('Concurrent operation still in progress.');
        $this->locks[]=$token;
    }
    public function close(): void {
        if ($this->pdo->inTransaction()) $this->pdo->rollBack();
        foreach (array_reverse($this->locks) as $token) $this->execute('SELECT RELEASE_LOCK(?)',[$token]);
        $this->locks=[];
    }
}

function require_key(?string $key): string {
    if ($key===null || $key==='' || preg_match('/^\s|\s$/u',$key) || preg_match_all('/./us',$key)>128) {
        throw new BusinessError(422,'INVALID_IDEMPOTENCY_KEY','Use a nonblank key of 1 to 128 characters without surrounding spaces.');
    }
    return $key;
}

function local_idempotent(string $scope,string $key,array $payload,callable $operation,string $cid): array {
    require_key($key);
    $fingerprint=hash('sha256',json_text(canonical($payload)));
    $db=new Database();
    try {
        $db->lock('idempotency:'.$scope.':'.$key);
        $db->pdo->beginTransaction();
        $old=$db->one('SELECT * FROM idempotency_records WHERE scope=? AND idem_key=?',[$scope,$key]);
        if ($old!==null) {
            if (!hash_equals($old['fingerprint'],$fingerprint)) {
                throw new BusinessError(409,'IDEMPOTENCY_CONFLICT','This key was already used with a different request payload.');
            }
            $db->pdo->commit();
            log_event('idempotency_replay',$cid,['scope'=>$scope,'key_hash'=>substr(hash('sha256',$key),0,12)]);
            return [(int)$old['http_status'],json_decode($old['response_body'],true,512,JSON_THROW_ON_ERROR)];
        }
        $db->execute('INSERT INTO idempotency_records(scope,idem_key,fingerprint) VALUES (?,?,?)',[$scope,$key,$fingerprint]);
        $db->execute('SAVEPOINT effect');
        try {
            [$status,$body]=$operation($db);
            $db->execute('RELEASE SAVEPOINT effect');
        } catch (BusinessError $error) {
            $db->execute('ROLLBACK TO SAVEPOINT effect');
            $db->execute('RELEASE SAVEPOINT effect');
            $status=$error->status;$body=$error->body();
        }
        $db->execute('UPDATE idempotency_records SET http_status=?,response_body=? WHERE scope=? AND idem_key=?',
                     [$status,json_text($body),$scope,$key]);
        $db->pdo->commit();
        return [$status,$body];
    } finally {
        $db->close();
    }
}

function request_body(): array {
    $raw=file_get_contents('php://input');
    if (strlen($raw)>65536) throw new BusinessError(422,'VALIDATION_ERROR','The request body is too large.');
    try {
        $object=json_decode($raw,false,512,JSON_THROW_ON_ERROR);
        if (!is_object($object)) throw new \JsonException('Expected JSON object');
        return json_decode($raw,true,512,JSON_THROW_ON_ERROR);
    } catch (\JsonException $error) {
        throw new BusinessError(422,'VALIDATION_ERROR','Send a valid JSON object.');
    }
}

function fields(array $payload,array $allowed,array $required): void {
    if (array_diff(array_keys($payload),$allowed) || array_diff($required,array_keys($payload))) {
        throw new BusinessError(422,'VALIDATION_ERROR','The request has missing or unexpected fields.');
    }
}

function uuid_field(mixed $value): string {
    if (!is_string($value) || !preg_match('/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/iD',$value)) {
        throw new BusinessError(422,'VALIDATION_ERROR','A valid UUID is required.');
    }
    return strtolower($value);
}

function text_field(mixed $value,int $max): string {
    if (!is_string($value) || $value==='' || preg_match_all('/./us',$value)>$max) {
        throw new BusinessError(422,'VALIDATION_ERROR','A required text field is invalid.');
    }
    return $value;
}

function serve(callable $router): void {
    ignore_user_abort(true);
    $candidate=$_SERVER['HTTP_X_CORRELATION_ID'] ?? '';
    $cid=preg_match('/^[\x20-\x7e]{1,128}$/D',$candidate) ? $candidate : uuid4();
    $path=parse_url($_SERVER['REQUEST_URI'],PHP_URL_PATH);
    $method=$_SERVER['REQUEST_METHOD'];
    try {
        if (in_array($path,['/health','/openapi.json'],true) && $method!=='GET') {
            throw new BusinessError(405,'HTTP_ERROR','Method Not Allowed');
        } elseif ($method==='GET' && $path==='/health') {
            $db=new Database();
            try { $db->one('SELECT 1'); } finally { $db->close(); }
            [$status,$body]=[200,['status'=>'ok','service'=>service_name()]];
        } elseif ($method==='GET' && $path==='/openapi.json') {
            [$status,$body]=[200,json_decode(file_get_contents(SERVICE_HOME.'/openapi.json'),true,512,JSON_THROW_ON_ERROR)];
        } else {
            [$status,$body]=$router($method,$path,$cid);
        }
    } catch (BusinessError $error) {
        $status=$error->status;$body=$error->body();
    } catch (OperationBusy $error) {
        $status=503;$body=(new BusinessError(503,'SERVICE_BUSY','A concurrent operation is still running; retry the same request key.'))->body();
    } catch (\PDOException $error) {
        log_event('database_error',$cid,['exception'=>get_class($error)]);
        $status=503;$body=(new BusinessError(503,'DATABASE_UNAVAILABLE','The service database is temporarily unavailable.'))->body();
    } catch (\Throwable $error) {
        log_event('unexpected_error',$cid,['exception'=>get_class($error)]);
        $status=500;$body=(new BusinessError(500,'INTERNAL_ERROR','The service could not complete the request.'))->body();
    }
    http_response_code($status);
    header('Content-Type: application/json; charset=utf-8');
    header('X-Correlation-ID: '.$cid);
    log_event('http_request',$cid,['method'=>$method,'path'=>$path,'status'=>$status]);
    echo json_text($body);
    exit;
}

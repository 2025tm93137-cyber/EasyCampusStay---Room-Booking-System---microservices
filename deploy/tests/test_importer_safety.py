import contextlib,hashlib,importlib.util,io,json,shutil,subprocess,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/'evidence/assignment2/setup'
(BASE/'qa').mkdir(parents=True,exist_ok=True)

spec=importlib.util.spec_from_file_location('a2importer',ROOT/'deploy/import_assignment2.py')
mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
def call(*args):
 return subprocess.run(list(map(str,args)),capture_output=True,text=True,check=True)
class ImportSafety(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory(prefix='a2-import-check-')
  self.base=Path(self.tmp.name);self.target=self.base/'checkout';self.target.mkdir()
  for f in set(mod.REQUIRED)|set(mod.PATCH_FILES):
   p=self.target/f;p.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/f,p)
  call('git','init','-q',self.target)
  call('git','-C',self.target,'apply','--reverse',ROOT/'deploy/patches/assignment2-existing-files.patch')
  self.commit()
  (self.target/'.env').write_text('PRIVATE_FIXTURE_DO_NOT_REPLACE=true\n')
 def tearDown(self):self.tmp.cleanup()
 def commit(self):
  call('git','-C',self.target,'add','.')
  call('git','-C',self.target,'-c','user.name=Importer verification fixture',
       '-c','user.email=fixture@example.test','commit','-qm','Isolated test fixture')
 def run_import(self,*opts):
  with patch.object(sys,'argv',['importer','--target',str(self.target),*opts]), \
       patch.object(Path,'home',return_value=self.base/'profile'),contextlib.redirect_stdout(io.StringIO()):
   return mod.main()
 def test_preview_writes_nothing(self):
  before={str(p.relative_to(self.target)):p.read_bytes() for p in self.target.rglob('*') if p.is_file()}
  self.assertEqual(self.run_import(),0)
  after={str(p.relative_to(self.target)):p.read_bytes() for p in self.target.rglob('*') if p.is_file()}
  self.assertEqual(before,after)
 def test_apply_preserves_private_config_and_business_source(self):
  p=self.target/'requirements.lock.txt';before=p.read_bytes()
  self.assertEqual(self.run_import('--apply'),0)
  self.assertTrue((self.target/'deploy/configure.py').is_file())
  self.assertTrue((self.target/'deploy/import_manifest.json').is_file())
  self.assertEqual(p.read_bytes(),before)
  self.assertEqual((self.target/'.env').read_text(),'PRIVATE_FIXTURE_DO_NOT_REPLACE=true\n')
  for f in mod.PATCH_FILES:self.assertEqual((self.target/f).read_bytes(),(ROOT/f).read_bytes())
 def test_divergent_member_patch_stops_before_any_import(self):
  (self.target/'ui/bootstrap.php').write_text('<?php // newer member implementation\n')
  self.commit()
  with self.assertRaisesRegex(ValueError,'patch conflicts'):self.run_import('--apply')
  self.assertFalse((self.target/'docker-compose.yml').exists())
  self.assertIn('newer member',(self.target/'ui/bootstrap.php').read_text())
 def test_dirty_checkout_is_preserved(self):
  p=self.target/'requirements.lock.txt';p.write_text(p.read_text()+'\n# actual unfinished work\n')
  with self.assertRaisesRegex(ValueError,'working tree must be clean'):self.run_import('--apply')
  self.assertFalse((self.target/'docker-compose.yml').exists())
  self.assertIn('unfinished work',p.read_text())
 def test_conflicting_deployment_file_requires_review(self):
  (self.target/'.dockerignore').write_text('# team deployment work\n');self.commit()
  with self.assertRaisesRegex(ValueError,'Review conflicting'):self.run_import('--apply')
  self.assertEqual((self.target/'.dockerignore').read_text(),'# team deployment work\n')
  self.assertFalse((self.target/'deploy').exists())
 def test_explicit_reviewed_replacement_has_external_backup(self):
  (self.target/'.dockerignore').write_text('# reviewed old settings\n');self.commit()
  self.run_import('--apply','--replace-reviewed')
  self.assertEqual((self.target/'.dockerignore').read_bytes(),(ROOT/'.dockerignore').read_bytes())
  backups=list((self.base/'profile/EasyCampusStay_A2_Backups').glob('*/.dockerignore'))
  self.assertEqual(len(backups),1)
  self.assertEqual(backups[0].read_text(),'# reviewed old settings\n')
 def test_symlink_escape_is_blocked(self):
  outside=self.base/'outside';outside.mkdir()
  try: (self.target/'deploy').symlink_to(outside,target_is_directory=True)
  except OSError: self.skipTest('Symbolic links are unavailable for this account')
  with self.assertRaisesRegex(ValueError,'escapes project'):self.run_import('--apply')
  self.assertEqual(list(outside.iterdir()),[])
 def test_corrupt_package_hash_is_detected(self):
  source=self.base/'source';source.mkdir()
  manifest=json.loads((ROOT/'deploy/import_manifest.json').read_text())
  for relative in [*manifest['files'], 'deploy/import_manifest.json']:
   dst=source/relative;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/relative,dst)
  (source/'deploy/configure.py').write_text('# incomplete download\n')
  with patch.object(mod,'SOURCE',source):
   with self.assertRaisesRegex(ValueError,'incomplete or changed'):self.run_import('--apply')
  self.assertFalse((self.target/'docker-compose.yml').exists())
 def test_repeated_import_skips_identical_files_and_patches(self):
  self.run_import('--apply');self.commit()
  before=(self.target/'ui/bootstrap.php').read_bytes()
  self.assertEqual(self.run_import('--apply'),0)
  self.assertEqual((self.target/'ui/bootstrap.php').read_bytes(),before)
  self.assertEqual(call('git','-C',self.target,'status','--porcelain').stdout.strip(),'')

if __name__=='__main__':
 suite=unittest.defaultTestLoader.loadTestsFromTestCase(ImportSafety)
 stream=io.StringIO();r=unittest.TextTestRunner(stream=stream,verbosity=2).run(suite)
 text=stream.getvalue();print(text)
 (BASE/'qa/importer-test-output.txt').write_text(text)
 (BASE/'qa/importer-tests.json').write_text(json.dumps({'platform':sys.platform,'python':sys.version.split()[0],
  'verification_scope':'deployment file import only','docker_runtime_executed':False,'kubernetes_runtime_executed':False,
  'cases':r.testsRun,'failures':len(r.failures),'errors':len(r.errors),'skipped':len(r.skipped),'result':'PASS' if r.wasSuccessful() else 'FAIL'},indent=2)+'\n')
 raise SystemExit(not r.wasSuccessful())

"""Export specs from the running APIs, not hand-maintained approximations."""
import json
from common import NAMES,ROOT,request


if __name__=='__main__':
    folder=ROOT/'docs'/'openapi'
    folder.mkdir(parents=True,exist_ok=True)
    for name in NAMES:
        response=request(name,'GET','/openapi.json')
        assert response.status_code==200,response.text
        (folder/(name+'.json')).write_text(json.dumps(response.json(),indent=2)+'\n')
        print('Exported docs/openapi/'+name+'.json')

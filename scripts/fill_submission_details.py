"""Enter real personal/submission fields; never generates a fictional contribution history."""
import json
from pathlib import Path
import re

ROOT=Path(__file__).resolve().parents[1]


def ask(label,previous=''):
    value=input(label+(' ['+previous+']' if previous else '')+': ').strip()
    return value or previous


def main():
    target=ROOT/'docs/submission.json'
    old=json.loads(target.read_text()) if target.exists() else {}
    team=ask('Actual team name',old.get('team_name',''))
    count=int(input('Number of actual members (1-4): ').strip())
    if not 1<=count<=4:raise SystemExit('The institution allows at most four members.')
    students=[]
    for index in range(count):
        previous=(old.get('students',[])+[{}]*4)[index]
        print('\nMember',index+1)
        name=ask('Real full name',previous.get('name',''))
        student_id=ask('Student ID',previous.get('student_id',''))
        service=ask('Actual responsibility/service',previous.get('service',''))
        contribution=ask('Work actually performed',previous.get('contribution',''))
        commit=ask('Genuine contribution commit URL or hash',previous.get('commit',''))
        slug=re.sub(r'[^A-Za-z0-9_-]','_',student_id or 'member_'+str(index+1))
        reflection='docs/reflections/'+slug+'.md'
        path=ROOT/reflection;path.parent.mkdir(exist_ok=True)
        if not path.exists():
            path.write_text('# Personal reflection worksheet: '+name+'\n\nStudent ID: '+student_id+'\n\nWrite approximately half a page in your own words.\n\n1. Work I actually performed:\n\n2. Hardest problem I personally solved:\n\n3. Tests/evidence and what I learned:\n\n4. What I would change next:\n\n5. Actual AI assistance and my verification:\n',encoding='utf-8')
        students.append({'name':name,'student_id':student_id,'service':service,'contribution':contribution,'commit':commit,'reflection':reflection})
    result={'team_name':team,'students':students,'github_url':ask('Actual GitHub repository URL',old.get('github_url','')),
            'google_drive_url':ask('Actual Google Drive supporting-material folder URL',old.get('google_drive_url','')),
            'video_url':ask('Actual video URL (can remain blank while recording is pending)',old.get('video_url',''))}
    target.write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    print('\nSaved docs/submission.json and individual worksheets. Complete your own reflections, then rebuild/review the PDFs.')


if __name__=='__main__':main()

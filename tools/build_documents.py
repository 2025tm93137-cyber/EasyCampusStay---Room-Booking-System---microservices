"""Build the four editable CampusStay PDFs. Run from any working directory."""
from __future__ import annotations
import html
import json
import math
from pathlib import Path
import re
import textwrap
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (BaseDocTemplate, Frame, PageTemplate, Paragraph,
    Spacer, PageBreak, LongTable, TableStyle, XPreformatted, KeepTogether)
from reportlab.graphics.shapes import Drawing, Rect, Line, Polygon, String

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / 'docs'
FONT = ROOT / 'tools/fonts'
for name, file in [('CS','DejaVuSans.ttf'),('CSBold','DejaVuSans-Bold.ttf'),('CSMono','DejaVuSansMono.ttf')]:
    pdfmetrics.registerFont(TTFont(name,str(FONT/file)))
pdfmetrics.registerFontFamily('CS',normal='CS',bold='CSBold',italic='CS',boldItalic='CSBold')
TEAL=colors.HexColor('#136f70'); INK=colors.HexColor('#193c43'); GRAY=colors.HexColor('#536871')
PALE=colors.HexColor('#edf6f5'); BORDER=colors.HexColor('#d2e2e2')
W,H=A4; LEFT=48; RIGHT=48; WIDTH=W-LEFT-RIGHT
S={
 'title':ParagraphStyle('title',fontName='CSBold',fontSize=23,leading=28,textColor=INK,spaceAfter=15,keepWithNext=True),
 'h2':ParagraphStyle('h2',fontName='CSBold',fontSize=15,leading=20,textColor=TEAL,spaceBefore=14,spaceAfter=9,keepWithNext=True),
 'h3':ParagraphStyle('h3',fontName='CSBold',fontSize=12,leading=16,textColor=INK,spaceBefore=10,spaceAfter=6,keepWithNext=True),
 'body':ParagraphStyle('body',fontName='CS',fontSize=10.5,leading=15,spaceAfter=9,splitLongWords=True),
 'guide':ParagraphStyle('guide',fontName='CS',fontSize=11,leading=16,spaceAfter=9,splitLongWords=True),
 'cell':ParagraphStyle('cell',fontName='CS',fontSize=9.2,leading=12.8,spaceAfter=0,splitLongWords=True),
 'head':ParagraphStyle('head',fontName='CSBold',fontSize=9.2,leading=12.8,textColor=colors.white,spaceAfter=0),
 'code':ParagraphStyle('code',fontName='CSMono',fontSize=9.2,leading=13,spaceAfter=0,textColor=INK),
}


def inline(value):
    value=html.escape(value)
    value=re.sub(r'`([^`]+)`',r'<font name="CSMono">\1</font>',value)
    value=re.sub(r'\*\*([^*]+)\*\*',r'<b>\1</b>',value)
    value=re.sub(r'\[([^\]]+)\]\((https?://[^ )]+)\)',r'<link href="\2" color="#136f70">\1</link>',value)
    return value


class Document(BaseDocTemplate):
    def __init__(self,path,title,report=False):
        super().__init__(str(path),pagesize=A4,leftMargin=LEFT,rightMargin=RIGHT,
            topMargin=57,bottomMargin=48,title=title,author='CampusStay - AI-assisted baseline')
        self.caption=title; self.report=report; self.headings=[]; self.appendix_page=None
        self.addPageTemplates(PageTemplate(id='normal',frames=[Frame(LEFT,48,WIDTH,H-105,
            leftPadding=0,rightPadding=0,topPadding=0,bottomPadding=0)],onPage=self.decorate))
    def decorate(self,c,doc):
        c.saveState(); c.setFillColor(TEAL); c.rect(0,H-9,W,9,fill=1,stroke=0)
        c.setFont('CSBold',8); c.drawString(LEFT,H-33,'CAMPUSSTAY  /  OPTION B')
        c.setFont('CS',7.7); c.setFillColor(GRAY)
        c.drawRightString(W-RIGHT,H-33,'SEZG583 - Assignment 1')
        c.setStrokeColor(BORDER); c.line(LEFT,36,W-RIGHT,36)
        c.drawString(LEFT,23,self.caption[:78]); c.drawRightString(W-RIGHT,23,str(doc.page))
        c.restoreState()
    def afterFlowable(self,f):
        if isinstance(f,Paragraph) and f.style.name in ['h2','title']:
            title=f.getPlainText(); self.headings.append({'title':title,'page':self.page})
            key='heading'+str(len(self.headings)); self.canv.bookmarkPage(key)
            self.canv.addOutlineEntry(title,key,level=0,closed=False)
            if title.startswith('Appendix A.') and self.appendix_page is None:self.appendix_page=self.page


def box(d,x,y,w,h,title,lines=()):
    d.add(Rect(x,y,w,h,rx=5,fillColor=PALE,strokeColor=BORDER))
    d.add(String(x+9,y+h-17,title,fontName='CSBold',fontSize=9.5,fillColor=INK))
    for i,line in enumerate(lines):
        d.add(String(x+9,y+h-33-12*i,line,fontName='CS',fontSize=8.4,fillColor=GRAY))


def arrow(d,x1,y1,x2,y2,label=None):
    d.add(Line(x1,y1,x2,y2,strokeColor=TEAL,strokeWidth=1.1))
    a=math.atan2(y2-y1,x2-x1); size=5
    d.add(Polygon([x2,y2,x2-size*math.cos(a-.5),y2-size*math.sin(a-.5),
        x2-size*math.cos(a+.5),y2-size*math.sin(a+.5)],fillColor=TEAL,strokeColor=TEAL))
    if label:d.add(String((x1+x2)/2+4,(y1+y2)/2+4,label,fontName='CS',fontSize=8,fillColor=GRAY))


def diagram(kind):
    if kind=='component':
        d=Drawing(WIDTH,216)
        box(d,175,174,150,37,'PHP console :8180')
        box(d,175,111,150,45,'Reservation :8102',['Python / FastAPI'])
        arrow(d,250,174,250,157,'REST')
        for x,title,port,lang,db in [(0,'Inventory',8101,'Python','inventory'),(175,'Payment',8103,'PHP mock','payment'),(350,'Notification',8104,'PHP mock','notification')]:
            box(d,x,40,148,45,f'{title} :{port}',[lang])
            arrow(d,250,111,x+74,87)
            box(d,x,0,148,27,f'Own {db} DB')
            arrow(d,x+74,40,x+74,28)
        box(d,0,125,148,31,'Own reservation DB'); arrow(d,175,138,149,138)
        return d
    if kind=='sequence':
        d=Drawing(WIDTH,215); xs=[36,145,252,359,466]
        for x,t in zip(xs,['Client/UI','Reservation','Inventory','Payment','Notification']):
            d.add(String(x,200,t,textAnchor='middle',fontName='CSBold',fontSize=8.5,fillColor=INK))
            d.add(Line(x,10,x,188,strokeColor=BORDER,strokeDashArray=[3,3]))
        for y,i,j,t in [(176,0,1,'1 Create booking'),(143,1,2,'2 Hold stock'),(110,1,3,'3 Charge'),(77,1,2,'4 Confirm hold'),(44,1,4,'5 Send confirmation'),(15,1,0,'201 / 202 / failure')]:
            arrow(d,xs[i],y,xs[j],y)
            d.add(String((xs[i]+xs[j])/2,y+6,t,textAnchor='middle',fontName='CS',fontSize=8.2,fillColor=GRAY))
        return d
    d=Drawing(WIDTH,145)
    if kind=='inventory_er':
        box(d,0,79,224,64,'room_types',['PK id; price_minor; currency'])
        box(d,275,79,224,64,'room_stock',['PK/FK room_type_id + stay_date','capacity; available'])
        box(d,275,0,224,65,'holds',['PK id; UNIQUE booking_id','FK stock; status; amount_minor'])
        box(d,0,0,224,65,'idempotency_records',['PK scope + idem_key','fingerprint; saved response'])
        arrow(d,224,111,274,111,'1:N'); arrow(d,387,79,387,66,'1:N')
    elif kind=='reservation_er':
        box(d,138,79,224,64,'bookings',['PK id; status; request_body','peer IDs have no cross-DB FK'])
        box(d,0,0,224,65,'booking_steps',['PK id; FK booking_id','from_state; to_state'])
        box(d,275,0,224,65,'idempotency_records',['PK scope + idem_key','UNIQUE/FK booking_id; response'])
        arrow(d,192,79,112,66,'1:N'); arrow(d,304,79,387,66,'1:1')
    elif kind=='payment_er':
        box(d,0,79,224,64,'payments',['PK id; UNIQUE booking_id','amount_minor; status'])
        box(d,275,79,224,64,'refunds',['PK id; UNIQUE/FK payment_id','amount_minor'])
        arrow(d,224,112,274,112,'1:0..1')
        box(d,138,0,224,65,'idempotency_records',['PK scope + idem_key','fingerprint; saved response'])
    elif kind=='notification_er':
        box(d,0,48,224,83,'notifications',['PK id; UNIQUE booking_id','recipient; status; attempts','simulation'])
        box(d,275,48,224,83,'idempotency_records',['PK scope + idem_key','fingerprint; saved response'])
    return d


def table(lines):
    rows=[[c.strip() for c in l.strip().strip('|').split('|')] for l in lines]
    rows=[row for row in rows if not all(re.fullmatch(r':?-+:?',c or '-') for c in row)]
    n=len(rows[0]); ratios=[1/n]*n
    if rows[0][:2]==['Service','Method and suffix']:ratios=[.18,.51,.31]
    if rows[0][0]=='Rule':ratios=[.09,.30,.32,.29]
    if rows[0][0]=='Decision':ratios=[.28,.35,.37]
    if rows[0]==['Service','Responsibility','Technology','Own database']:ratios=[.18,.25,.24,.33]
    widths=[WIDTH*r for r in ratios]
    cells=[[Paragraph(inline(c),S['head' if i==0 else 'cell']) for c in row] for i,row in enumerate(rows)]
    t=LongTable(cells,colWidths=widths,repeatRows=1,hAlign='LEFT')
    t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),TEAL),('VALIGN',(0,0),(-1,-1),'TOP'),
        ('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,PALE]),('LINEBELOW',(0,0),(-1,0),.5,TEAL),
        ('LEFTPADDING',(0,0),(-1,-1),7),('RIGHTPADDING',(0,0),(-1,-1),7),
        ('TOPPADDING',(0,0),(-1,-1),6),('BOTTOMPADDING',(0,0),(-1,-1),6)]))
    return t


def outside_space(line,limit):
    quote=None; positions=[]
    for i,c in enumerate(line[:limit+1]):
        if c in ['"',"'"]:
            if quote==c:quote=None
            elif quote is None:quote=c
        if c==' ' and quote is None:positions.append(i)
    return positions[-1] if positions else None


def code_block(lines,language):
    rendered=[]
    for raw in lines:
        raw=raw.expandtabs(4)
        if language.lower() in ['powershell','ps1']:
            while len(raw)>86:
                cut=outside_space(raw,82)
                if cut is None or cut<8:break
                rendered.append(raw[:cut].rstrip()+' `'); raw='  '+raw[cut:].strip()
        rendered.append(raw)
    result=[Spacer(1,3)]
    for line in rendered:
        style=ParagraphStyle('codeline',parent=S['code'])
        measured=pdfmetrics.stringWidth(line,'CSMono',style.fontSize)
        if measured>WIDTH-18:
            style.fontSize=max(7.0,style.fontSize*(WIDTH-18)/measured)
        result.append(XPreformatted(html.escape(line or ' '),style))
    result.append(Spacer(1,12)); return result


def parse(markdown,guide=False):
    body=S['guide' if guide else 'body']; lines=markdown.splitlines(); out=[]; i=0
    while i<len(lines):
        line=lines[i].strip()
        if not line:i+=1;continue
        if line=='<!-- page -->':out.append(PageBreak());i+=1;continue
        if line.startswith('<!-- diagram:'):
            out.extend([Spacer(1,4),diagram(line.split(':',1)[1].split(' ',1)[0]),Spacer(1,10)]);i+=1;continue
        if line.startswith('<!--'):i+=1;continue
        if line.startswith('```'):
            language=line[3:].strip(); block=[];i+=1
            while i<len(lines) and not lines[i].strip().startswith('```'):block.append(lines[i]);i+=1
            out.extend(code_block(block,language));i+=1;continue
        if line.startswith('|'):
            rows=[]
            while i<len(lines) and lines[i].strip().startswith('|'):rows.append(lines[i]);i+=1
            out.extend([table(rows),Spacer(1,12)]);continue
        if line.startswith('#'):
            count=len(line)-len(line.lstrip('#')); content=line[count:].strip()
            out.append(Paragraph(inline(content),S['title' if count==1 else 'h2' if count==2 else 'h3']));i+=1;continue
        item=re.match(r'^([-*]|\d+\.)\s+(.*)',line)
        if item:
            label=item.group(1); content=item.group(2)
            style=ParagraphStyle('list',parent=body,leftIndent=15,firstLineIndent=-12,spaceAfter=7)
            out.append(Paragraph(inline(('•' if label in ['-','*'] else label)+' '+content),style));i+=1;continue
        p=[line];i+=1
        while i<len(lines) and lines[i].strip() and not re.match(r'^(#|\||```|<!--|[-*] |\d+\. )',lines[i].strip()):p.append(lines[i].strip());i+=1
        out.append(Paragraph(inline(' '.join(p)),body))
    return out


def load(path):
    return json.loads(path.read_text(encoding='utf-8')) if path.exists() else {}


def fields():
    meta=load(DOCS/'submission.json'); run=load(ROOT/'evidence/tests/run_summary.json')
    con=load(ROOT/'evidence/challenge-1-concurrency/results.json')
    idem=load(ROOT/'evidence/challenge-2-idempotency/results.json')
    ui=load(ROOT/'evidence/tests/ui_validation.json')
    members=meta.get('students',[])
    pending=not members or not all(meta.get(k) for k in ['team_name','github_url','google_drive_url','video_url'])
    contributions='**PENDING: enter real names, IDs, responsibilities, actual work and genuine commit references.**'
    reflections='**PENDING: each actual member must complete their own half-page reflection.**'
    if members:
        contributions='| Name / student ID | Responsibility | Work actually performed | Genuine commit |\n|---|---|---|---|\n'
        reflections=''
        for m in members:
            safe=lambda s:str(s or 'PENDING').replace('|','/')
            contributions+='| '+safe(m.get('name'))+' / '+safe(m.get('student_id'))+' | '+safe(m.get('service'))+' | '+safe(m.get('contribution'))+' | '+safe(m.get('commit'))+' |\n'
            ref=m.get('reflection',''); candidate=(ROOT/ref).resolve()
            content='PENDING: write and review the personal reflection.'
            if ref and candidate.is_relative_to(ROOT) and candidate.is_file():content=candidate.read_text(encoding='utf-8')
            reflections+='### '+safe(m.get('name'))+'\n\n'+content+'\n\n'
    return {
        'team_name':meta.get('team_name') or 'TEAM DETAILS PENDING',
        'draft_notice':'**DRAFT: actual team details, contribution entries, reflections and submission links must be completed.**' if pending else '**Review the actual personal fields, reflections, evidence and faculty access before submission.**',
        'github_url':meta.get('github_url') or 'PENDING - actual faculty-accessible repository',
        'google_drive_url':meta.get('google_drive_url') or 'PENDING - actual supporting-material folder',
        'video_url':meta.get('video_url') or 'PENDING - actual team-recorded video',
        'contributions':contributions,'reflections':reflections,
        'run_result':run.get('result','NOT RUN'),'run_time':run.get('finished_at','NOT RUN'),
        'runtime':f"{run.get('actual_os','unknown')}; Python {run.get('python_version','?')}; PHP {run.get('php_version','?')}; database {run.get('database_engine','?')}",
        'concurrency_result':f"{con.get('requests','?')} requests; capacity {con.get('capacity','?')}; HTTP counts {con.get('counts',{})}",
        'idempotency_result':f"{len(idem.get('simultaneous_first_calls',[]))} simultaneous calls; changed payload returned {idem.get('payload_conflict',{}).get('http_status','?')}",
        'ui_result':f"{ui.get('result','NOT RUN')} on {ui.get('actual_os','unknown')}; {len(ui.get('checks',[]))} browser checks, separately timestamped",
    }


def main():
    values=fields(); summaries=[]
    jobs=[('PROPOSAL.md','CampusStay_Proposal.pdf','Project proposal',False),
          ('DESIGN_REPORT.md','CampusStay_Design_Report.pdf','Design and implementation report',False),
          ('BEGINNER_WINDOWS_GUIDE.md','CampusStay_Beginner_Windows_Git_to_Video_Guide.pdf','Beginner Windows, Git and submission guide',True),
          ('DEMO_VIDEO_GUIDE.md','CampusStay_Demo_Video_Guide.pdf','Team demonstration recording guide',True)]
    for src,name,title,guide in jobs:
        text=(DOCS/src).read_text(encoding='utf-8')
        for key,value in values.items():text=text.replace('{{'+key+'}}',str(value))
        if re.search(r'\{\{[a-z_]+\}\}',text):raise ValueError('Unresolved report field in '+src)
        doc=Document(DOCS/name,title,report=src=='DESIGN_REPORT.md');doc.build(parse(text,guide))
        if doc.report and (doc.appendix_page is None or doc.appendix_page-1>15):
            raise RuntimeError('Report exceeds 15 main pages or has no appendix: '+str(doc.appendix_page))
        summaries.append({'file':name,'pages':doc.page,'main_pages':doc.appendix_page-1 if doc.report else None,'headings':doc.headings})
        print(name,':',doc.page,'pages',('; main body '+str(doc.appendix_page-1)) if doc.report else '')
    (DOCS/'document_build.json').write_text(json.dumps(summaries,indent=2)+'\n',encoding='utf-8')


if __name__=='__main__':main()

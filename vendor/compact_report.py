"""Concise parent-facing reports: fixed 1/2 pages, editable Word + vector charts."""
import io, math, zipfile
from xml.sax.saxutils import escape
from collections import defaultdict
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.lib.colors import HexColor, white
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
import pypdfium2

NAVY='#113451'; TEAL='#16898b'; COLORS=[NAVY,'#248dbe','#e6a23b','#6aab81','#8b73ad','#8b9dad']
ABILITIES=['概念理解','模型建构','实验探究','运算推理','规范表达']
def short(s,n):
    s=' '.join(str(s or '').split());return s if len(s)<=n else s[:n-1]+'…'
def groups(d,key):
    result=defaultdict(lambda:[0,0,0])
    for q in d['questions']:
        v=result[q[key]];v[0]+=q['max']
        if q['score'] is not None:v[1]+=q['score'];v[2]+=q['max']
    return result
def stats(d):
    qs=d['questions'];return sum(q['max'] for q in qs),sum(q['score'] or 0 for q in qs),sum(q['max'] for q in qs if q['score'] is not None)
def top_topics(d):
    items=sorted(((k,v[0]) for k,v in groups(d,'topic').items()),key=lambda a:-a[1])
    return items if len(items)<=5 else items[:4]+[('其他考点',sum(v for _,v in items[4:]))]
def priorities(d):
    qs=[q for q in d['questions'] if q['score'] is None or q['score']<q['max']]
    return sorted(qs,key=lambda q:(q['score'] is None,-(q['max']-(q['score'] or 0))))
def text(c,s,x,y,size=10,color=NAVY):
    c.setFillColor(HexColor(color));c.setFont('STSong-Light',size);c.drawString(x,y,str(s))
def wrap(c,s,x,y,width,size=10,lines=4,leading=16):
    s=' '.join(str(s or '').split());line='';rows=[]
    for char in s:
        if pdfmetrics.stringWidth(line+char,'STSong-Light',size)>width:rows.append(line);line=char
        else:line+=char
    if line:rows.append(line)
    if len(rows)>lines:rows=rows[:lines];rows[-1]=rows[-1][:-1]+'…'
    for i,row in enumerate(rows):text(c,row,x,y-i*leading,size)
    return y-len(rows)*leading
def panel(c,title,x,y,w,h):
    c.setFillColor(HexColor('#f8fafc'));c.setStrokeColor(HexColor('#d6e1e9'));c.roundRect(x,y,w,h,7,fill=1,stroke=1)
    text(c,title,x+12,y+h-22,12);c.setStrokeColor(HexColor('#d6e1e9'));c.line(x+10,y+h-32,x+w-10,y+h-32)
def chart(c,kind,d,x,y,w,h):
    if kind=='topic':
        items=top_topics(d);total=sum(v for _,v in items);cx=x+w*.25;cy=y+h*.51;r=min(w*.22,h*.39);start=90
        for i,(k,v) in enumerate(items):
            extent=360*v/total;c.setFillColor(HexColor(COLORS[i]));c.wedge(cx-r,cy-r,cx+r,cy+r,start,extent,fill=1,stroke=0);start+=extent
        c.setFillColor(white);c.circle(cx,cy,r*.53,fill=1,stroke=0);text(c,'考点',cx-10,cy-3,10)
        for i,(k,v) in enumerate(items):
            yy=y+h-18-i*24;c.setFillColor(HexColor(COLORS[i]));c.rect(x+w*.51,yy-1,7,7,fill=1,stroke=0);text(c,short(k,9),x+w*.51+12,yy,9);text(c,f'{v/total:.0%}',x+w-31,yy,9)
    else:
        if kind=='difficulty':
            g=groups(d,'difficulty');total=stats(d)[0];items=[(k,g.get(k,[0])[0]/total, f'{g.get(k,[0])[0]:g}分') for k in ['基础','中档','提升']]
        elif kind=='ability':
            g=groups(d,'ability');items=[(k,(g[k][1]/g[k][2] if g[k][2] else None),f'{g[k][1]:g}/{g[k][2]:g}') for k in ABILITIES]
        else:
            g=groups(d,'type');items=[(k,v[1]/v[2] if v[2] else None,f'{v[1]:g}/{v[2]:g}') for k,v in g.items()][:6]
        gap=min(26,(h-12)/max(1,len(items)))
        for i,(name,rate,detail) in enumerate(items):
            yy=y+h-16-i*gap;text(c,short(name,7),x,yy,9);bx=x+67;bw=w-131;c.setFillColor(HexColor('#e5edf2'));c.roundRect(bx,yy-1,bw,8,3,fill=1,stroke=0)
            if rate is not None and rate>0:c.setFillColor(HexColor(COLORS[i%len(COLORS)]));c.roundRect(bx,yy-1,bw*rate,8,3,fill=1,stroke=0)
            text(c,(f'{rate:.0%}' if rate is not None else '待评估')+' '+detail,bx+bw+7,yy,8)
def header(c,d,page,pages):
    total,score,known=stats(d);c.setFillColor(HexColor(NAVY));c.rect(0,735,595.28,107,fill=1,stroke=0)
    text(c,d['institution']+'  /  '+d['stage']+'物理',30,814,10,'#b9d6e3');text(c,'物理学科测评分析报告',30,780,24,'#ffffff')
    text(c,short(d['exam'],43),30,750,10,'#ffffff');text(c,f"{d['student']}  ·  {d['grade']}  ·  分析教师 {d['teacher'] or '待填写'}",30,712,11)
    status='待教师校核' if any(not q['reviewed'] for q in d['questions']) else '教师已校核'
    text(c,f'已核得分 {score:g}/{known:g}    已录入分值 {total:g}    {status}',30,690,10)
    text(c,'仅反映本卷；未知分数不按零分处理；占比按已录入题目分值计算。',30,36,8,'#667c8a');text(c,f'{page} / {pages}',538,36,9)
def loss_rows(c,d,x,y,w,limit):
    rows=priorities(d); yy=y
    if not rows:text(c,'本次已录入题目未见已知失分；请结合材料完整性复核。',x,yy,10);return
    for q in rows[:limit]:
        loss='待核分' if q['score'] is None else f"失{q['max']-q['score']:g}分"
        text(c,f"第{q['id']}题  ·  {short(q['topic'],15)}  ·  {loss}",x,yy,11)
        yy=wrap(c,'诊断：'+(q['cause'] or '待核实原始作答'),x,yy-19,w,9.5,2,14)
        yy=wrap(c,'训练：'+(q['action'] or '待教师制定'),x,yy-3,w,9.5,2,14)-14
    if len(rows)>limit:text(c,f'本页列出优先项目，其余 {len(rows)-limit} 项保留在工作台逐题记录。',x,yy,9,'#667c8a')
def export_pdf(d):
    pdfmetrics.registerFont(UnicodeCIDFont('STSong-Light'));b=io.BytesIO();c=canvas.Canvas(b,pagesize=(595.28,841.89));pages=1 if d.get('reportPages')==1 else 2
    header(c,d,1,pages)
    panel(c,'01 整体难度评估',30,466,260,204);chart(c,'difficulty',d,42,535,236,92);wrap(c,d['summary'] or '待教师补充整体判断。',42,526,236,9.5,3,15)
    panel(c,'02 题型结构分析',304,466,260,204);chart(c,'type',d,316,489,236,132)
    panel(c,'03 考点分布',30,258,260,194);chart(c,'topic',d,42,272,236,138)
    panel(c,'04 学生能力画像',304,258,260,194);chart(c,'ability',d,316,278,236,132)
    if pages==1:
        panel(c,'05 失分与提分规划',30,58,534,186)
        yy=207
        for q in priorities(d)[:3]:
            loss='待核' if q['score'] is None else f"失{q['max']-q['score']:g}分"
            yy=wrap(c,f"第{q['id']}题 {q['topic']}（{loss}）：{q['cause']} 建议：{q['action']}",42,yy,510,9.5,2,14)-7
        wrap(c,'复测安排：'+d['plan'],42,yy,510,9,2,13)
    else:
        panel(c,'结论与材料范围',30,64,534,180);wrap(c,d.get('materialNotes') or '请先核查试卷、答题卡和评分标准是否齐全。',42,207,510,10,4,16)
        wrap(c,'沟通重点：'+d['followup'],42,128,510,10,3,16)
        c.showPage();header(c,d,2,pages);panel(c,'05 失分与提分规划',30,216,534,454);loss_rows(c,d,42,617,510,4)
        panel(c,'阶段训练与复测',30,64,534,138);wrap(c,d['plan'] or '根据错题优先级安排训练，并用新题复测。',42,163,510,10,5,16)
    c.save();return b.getvalue()

def chart_asset(kind,d):
    """PDF image fallback plus original SVG for modern Word vector display."""
    pdfmetrics.registerFont(UnicodeCIDFont('STSong-Light'));b=io.BytesIO();c=canvas.Canvas(b,pagesize=(270,140));chart(c,kind,d,5,5,260,130);c.save()
    pdf=pypdfium2.PdfDocument(b.getvalue());im=pdf[0].render(scale=2).to_pil();png=io.BytesIO();im.save(png,format='PNG');pdf.close()
    # Use the same statistics in SVG for vector Word rendering.
    elements=['<svg xmlns="http://www.w3.org/2000/svg" width="540" height="280" viewBox="0 0 270 140"><rect width="270" height="140" fill="white"/>']
    def tx(s,x,y,size=9):elements.append(f'<text x="{x}" y="{y}" font-family="Microsoft YaHei,SimSun" font-size="{size}" fill="{NAVY}">{escape(str(s))}</text>')
    if kind=='topic':
        items=top_topics(d);total=sum(v for _,v in items);ang=-math.pi/2;cx=65;cy=70;r=52
        for i,(k,v) in enumerate(items):
            end=ang+2*math.pi*v/total; x1=cx+r*math.cos(ang);y1=cy+r*math.sin(ang);x2=cx+r*math.cos(end);y2=cy+r*math.sin(end)
            if v==total:elements.append(f'<circle cx="65" cy="70" r="52" fill="{COLORS[i]}"/>')
            else:elements.append(f'<path d="M {cx} {cy} L {x1} {y1} A {r} {r} 0 {int(end-ang>math.pi)} 1 {x2} {y2} Z" fill="{COLORS[i]}"/>')
            elements.append(f'<rect x="131" y="{18+i*23}" width="7" height="7" fill="{COLORS[i]}"/>');tx(short(k,9),142,25+i*23,8);tx(f'{v/total:.0%}',240,25+i*23,8);ang=end
        elements.append('<circle cx="65" cy="70" r="27" fill="white"/>');tx('考点',55,74)
    else:
        g=groups(d,{'difficulty':'difficulty','ability':'ability','type':'type'}[kind]);total=stats(d)[0]
        keys=['基础','中档','提升'] if kind=='difficulty' else ABILITIES if kind=='ability' else list(g)[:6]
        for i,k in enumerate(keys):
            v=g.get(k,[0,0,0]);rate=v[0]/total if kind=='difficulty' else v[1]/v[2] if v[2] else None;y=13+i*23
            tx(short(k,7),3,y+8,9);elements.append(f'<rect x="70" y="{y}" width="130" height="8" rx="3" fill="#e5edf2"/>')
            if rate:elements.append(f'<rect x="70" y="{y}" width="{130*rate}" height="8" rx="3" fill="{COLORS[i%6]}"/>')
            tx(f'{rate:.0%}' if rate is not None else '待评估',207,y+8,8)
    elements.append('</svg>');return png.getvalue(),''.join(elements).encode()

def export_docx(d):
    doc=Document();sec=doc.sections[0];sec.page_width=Inches(8.27);sec.page_height=Inches(11.69);sec.top_margin=sec.bottom_margin=Inches(.48);sec.left_margin=sec.right_margin=Inches(.55)
    for name in ['Normal','Title','Heading 1','Heading 2']:
        s=doc.styles[name];s.font.name='Microsoft YaHei';s._element.get_or_add_rPr().rFonts.set(qn('w:eastAsia'),'微软雅黑');s.font.color.rgb=RGBColor(0,0,0);s.paragraph_format.space_after=Pt(4);s.paragraph_format.space_before=Pt(4)
    doc.styles['Normal'].font.size=Pt(9);doc.styles['Normal'].paragraph_format.line_spacing=1.1
    doc.styles['Title'].font.size=Pt(23);doc.styles['Heading 2'].font.size=Pt(12)
    # Strip built-in title border so Word does not add a blue rule.
    for s in [doc.styles['Title'],doc.styles['Normal']]:
        pp=s._element.find(qn('w:pPr'))
        if pp is not None:
            for el in list(pp):
                if el.tag==qn('w:pBdr'):pp.remove(el)
    pages=1 if d.get('reportPages')==1 else 2
    total,score,known=stats(d);status='待教师校核' if any(not q['reviewed'] for q in d['questions']) else '教师已校核'
    def heading():
        doc.add_paragraph('物理学科测评分析报告','Title');doc.add_paragraph(f"{d['institution']} · {d['stage']} · {d['grade']} · {d['student']}\n{short(d['exam'],46)}\n已核 {score:g}/{known:g} 分　已录入 {total:g} 分　{status}")
    heading();assets=[]
    grid=doc.add_table(rows=2,cols=2);grid.autofit=False
    for row in grid.rows:
        for cell in row.cells:cell.width=Inches(3.55)
    for cell,title,kind in zip([c for row in grid.rows for c in row.cells],['01 整体难度评估','02 题型结构分析','03 考点分布','04 学生能力画像'],['difficulty','type','topic','ability']):
        cell.paragraphs[0].style=doc.styles['Heading 2'];cell.paragraphs[0].text=title
        png,svg=chart_asset(kind,d);p=cell.add_paragraph();run=p.add_run();run.add_picture(io.BytesIO(png),width=Inches(3.25),height=Inches(1.65));assets.append((run,svg))
        if kind=='difficulty':cell.add_paragraph(short(d['summary'],90 if pages==2 else 55))
        elif kind=='type':cell.add_paragraph('柱长为已核部分得分率；待核分数不按零分处理。')
        elif kind=='topic':cell.add_paragraph('按已录入题目分值统计；合并展示低占比考点。')
        else:cell.add_paragraph('本卷得分率，仅反映对应题目的本次表现。')
    doc.add_paragraph('材料范围：'+short(d.get('materialNotes') or '待教师核查材料完整性。',150 if pages==2 else 65))
    if pages==2:doc.add_paragraph('沟通建议：'+short(d['followup'],160));doc.add_page_break();doc.add_heading('05 失分与提分规划',1)
    else:doc.add_heading('05 失分与提分规划',2)
    selected=priorities(d)[:4 if pages==2 else 3]
    for q in selected:
        loss='待核' if q['score'] is None else f"失{q['max']-q['score']:g}分"
        if pages==2:
            doc.add_heading(f"第{q['id']}题 {q['topic']} {loss}",2);doc.add_paragraph('诊断：'+short(q['cause'],95));doc.add_paragraph('证据：'+short(q['evidence'],100));doc.add_paragraph('训练：'+short(q['action'],85))
        else:doc.add_paragraph(f"第{q['id']}题 {short(q['topic'],12)}（{loss}）：{short(q['cause'],30)} 建议：{short(q['action'],28)}")
    if len(priorities(d))>len(selected):doc.add_paragraph('其余失分与待核项目保留在工作台逐题记录。')
    doc.add_heading('阶段训练与复测',2);doc.add_paragraph(short(d['plan'],350 if pages==2 else 85))
    if pages==2:doc.add_paragraph('判断边界：难度为内容估计，不是群体实测系数；能力画像不用于推断排名或长期能力。未校核项目需教师核对后再用于正式沟通。')
    # Add SVG source as DrawingML extension; PNG fallback supports older Word.
    for i,(run,svg) in enumerate(assets):
        from docx.opc.part import Part
        from docx.opc.packuri import PackURI
        part=Part(PackURI(f'/word/media/chart_vector_{i}.svg'),'image/svg+xml',svg,doc.part.package)
        rid=doc.part.relate_to(part,'http://schemas.openxmlformats.org/officeDocument/2006/relationships/image')
        blip=run._r.xpath('.//a:blip')[0];extlist=OxmlElement('a:extLst');ext=OxmlElement('a:ext');ext.set('uri','{96DAC541-7B7A-43D3-8B79-37D633B846F1}')
        from lxml import etree
        svgblip=etree.SubElement(ext,'{http://schemas.microsoft.com/office/drawing/2016/SVG/main}svgBlip');svgblip.set(qn('r:embed'),rid);extlist.append(ext);blip.append(extlist)
    b=io.BytesIO();doc.save(b);return b.getvalue()

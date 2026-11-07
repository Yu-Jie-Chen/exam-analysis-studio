"""A2, B2 printable records, and company acceptance record exports."""
import io,re
from xml.sax.saxutils import escape
from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,Table,TableStyle,PageBreak,KeepTogether
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.colors import HexColor
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from standards import scored,targets,attempt_result,retake_summary,CHECKS,audit,stats
NAVY='#173b55'
def styles():
    pdfmetrics.registerFont(UnicodeCIDFont('STSong-Light'))
    return {k:ParagraphStyle(k,fontName='STSong-Light',fontSize=z,leading=l,spaceAfter=a,wordWrap='CJK',keepWithNext=k=='h') for k,z,l,a in [('title',21,28,14),('h',13,19,8),('p',10.5,16,7),('small',9,14,4)]}
def P(text,style):return Paragraph(escape(str(text or '待补充')).replace('\n','<br/>'),style)
def table(rows,widths,st,header=False):
    t=Table([[P(v,st['small']) for v in row] for row in rows],colWidths=widths,repeatRows=1 if header else 0,hAlign='LEFT',splitInRow=1)
    commands=[('GRID',(0,0),(-1,-1),.45,HexColor('#d4dfe7')),('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),8),('RIGHTPADDING',(0,0),(-1,-1),8),('TOPPADDING',(0,0),(-1,-1),7),('BOTTOMPADDING',(0,0),(-1,-1),7)]
    if header:commands+=[('BACKGROUND',(0,0),(-1,0),HexColor('#e8eff4'))]
    t.setStyle(TableStyle(commands));return t
def build(d,story,title):
    b=io.BytesIO()
    def footer(c,doc):
        c.setFont('STSong-Light',9);c.setFillColor(HexColor('#667d8c'));c.drawString(38,24,d.get('institution','文源教育')+' · '+('正式交付' if d.get('exportMode')=='final' else '校核草稿'));c.drawRightString(557,24,str(doc.page))
    SimpleDocTemplate(b,pagesize=(595.28,841.89),leftMargin=38,rightMargin=38,topMargin=34,bottomMargin=40,title=title,author=d.get('teacher','')).build(story,onFirstPage=footer,onLaterPages=footer);return b.getvalue()
def identity(d):return f"{d['student']} · {d['grade']}\n{d['exam']}\n分析教师 {d['teacher'] or '待填写'}　分析日期 {d.get('analysisDate') or '待填写'}　版本 {d.get('version') or 'V1.0'}"
def detail_pdf(d):
    st=styles();total,score,known=stats(d);story=[P('详细题号分析报告',st['title']),P(identity(d),st['p']),P(f'共 {len(d["questions"])} 个计分单元 / {total:g} 分；已核得分 {score:g}/{known:g}。',st['p'])]
    if d.get('materialNotes'):story.append(P('材料范围 '+d['materialNotes'],st['p']))
    for q in d['questions']:
        known=scored(q);correct=known and q['score']==q['max'];scoretext=str(q['score']) if known else '待核'
        story.append(P(f"第{q['id']}题　{q['type']}　{q['topic']}　{scoretext}/{q['max']:g}分",st['h']))
        rows=[['考查与难度',q['topic']+'；'+q['difficulty']+'。'+q.get('difficultyReason','')],['主要能力',q['ability']+'；'+q.get('abilityTask','')],['原始作答',q.get('studentAnswer') or q['evidence']],['参考与来源',(q.get('referenceAnswer') or '参考结果待补')+'\n'+q.get('scoringSource','来源待补')]]
        if correct:
            rows += [['本题结论',(q.get('mastery') or '本题结果正确，理解情况需结合过程核实')+'；'+(q.get('challenge') or '')],['作答对照与分析',q.get('cause') or '本题结果正确，理解情况需结合过程核实。'],['关键解法与评分',q.get('solution','')+'\n'+q.get('scoringPoints','')],['保持与验收',q['action']+'\n'+q.get('acceptance','')]]
        else:
            rows += [['关键条件与难点',q.get('conditions','')+'\n'+q.get('challenge','')],['关键解法与评分点',q.get('solution','')+'\n'+q.get('scoringPoints','')],['掌握程度与原因',q.get('mastery','')+'；'+q.get('errorType','')+'\n'+q['cause']],['训练与验收',q['action']+'\n'+q.get('acceptance','')]]
        rows += [['追溯与校核',f"原卷 {q.get('sourcePage') or '页码待补'}；教师 {d['teacher']}；{'已校核' if q['reviewed'] else '待校核'}"+('；教学分类 '+q.get('teachingClass','') if d['service']=='B' else '')]]
        story.extend([table(rows,[105,414],st),Spacer(1,15)])
    return build(d,story,'详细题号分析报告')
def paper_pdf(d):
    st=styles();qs=targets(d)
    if not qs:raise ValueError('请先选择复做目标题')
    story=[]
    for i,q in enumerate(qs):
        if i:story.append(PageBreak())
        a=q.get('retake',{});result=attempt_result(a,q)
        story.extend([P('讲解与独立复做纸质记录',st['title']),P(identity(d),st['small']),P(f"第{q['id']}题 · {q['topic']} · {q['max']:g}分　{'核心题' if q.get('core') else '目标题'}",st['h'])])
        yes=lambda k:'是' if a.get(k) is True else '否' if a.get(k) is False else '待核'
        checklist=f"结果正确 {yes('resultCorrect')}；关键步骤全部正确 {yes('stepsCorrect')}\n必要表达 {yes('expressionComplete')}；独立完成 {yes('independent')}\n非关键规范 {a.get('normYes',0)}/{a.get('normTotal',0)}；事前约定 {yes('conditionsMet')}；用时 {a.get('minutes') if a.get('minutes') is not None else '待记'} 分钟" if a.get('reviewed') else '□结果正确　□关键步骤全部正确　□必要图示方向单位完整\n非关键规范：通过____项 / 适用____项；□符合事前时间工具约定'
        story.append(table([['教学范围',q.get('teachingClass') or '待分类'],['教学证据',q.get('teachingEvidence') or '待记录'],['关键验收点',q.get('criticalPoints') or '讲解前填写'],['核心方法',q.get('method') or q['topic']],['题干与原答',q.get('questionText') or '按原卷题号附题干；原始作答另附。'],['讲解记录',a.get('explanation') or '____________________________________________________________'],['独立复做',f"答卷位置 {a.get('evidence') or '________________'}；日期 {d.get('retakeDate') or '________'}\n开始 __________　结束 __________　实际用时 ________\n□未看答案或原订正　□未接受提示　□有帮助（说明）________________"],['学生答题要求','按需写清对象与条件、物理图示、规律依据、过程列式、计算单位和结论。收起讲义及答案，另纸独立作答。'],['逐项验收',checklist],['原题结论',result['status']+'；'+'、'.join(result['reasons']) if a.get('reviewed') else '□通过　□未通过　□未测（完成后由教师确认）']], [104,415],st))
        story.extend([Spacer(1,10),P('独立复做答卷另附　学生确认 __________　教师 __________　日期 __________',st['p']),P('变式复测',st['h'])])
        vs=[v for v in d.get('variants',[]) if v.get('method')==(q.get('method') or q['topic'])]
        story.append(P('；'.join(v.get('id','')+'：'+attempt_result(v)['status']+'，答卷 '+v.get('evidence','待补') for v in vs) or '变式题号 __________　答卷位置 __________　□通过 □未通过 □未测',st['p']))
        story.append(P('后续安排 '+(a.get('nextAction') or '________________________________________________'),st['p']))
    return build(d,story,'讲解与独立复做纸质记录')
def acceptance_pdf(d):
    st=styles();report=audit(d,'retake' if d['service']=='B' else 'first');rows=[['验收项目','结果','问题与定位']]
    for key,label in CHECKS:
        a=d.get('companyChecks',{}).get(key,{});applicable=key not in (['teaching','paper','comparison'] if d['service']=='A' else ['detail'])
        rows.append([label,a.get('status','待检查') if applicable else '不适用',a.get('note','')])
    story=[P('交付验收记录',st['title']),P(identity(d),st['p']),P(f"档案 {d.get('studentId') or '待填'}　服务 {d['service']}　复核 {d.get('reviewer') or '待填'}　日期 {d.get('reviewDate') or '待填'}",st['p']),table(rows,[240,75,204],st,True),Spacer(1,12),P('交付结论 '+report['status'],st['h'])]
    if d['service']=='B':
        r=retake_summary(d);story.append(P(f"学生学习验收 {r['status']}；原题加权通过率 {r['rate']:.0%}；核心题 {r['corePassed']}/{len(r['core'])}。",st['p']))
    if report['errors']:story.extend([P('待修改或待补事项',st['h']),P('\n'.join('• '+e for e in report['errors']),st['p'])])
    story.extend([P('责任人 __________　完成日期 __________　复验结果 __________',st['p']),P('复核签名 __________　确认日期 __________',st['p'])]);return build(d,story,'交付验收记录')

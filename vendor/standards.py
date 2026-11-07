"""Rules from the user's revised V1.0; report layout updated independently in final_report.py."""
import copy, math, re
ABILITIES=['概念理解','模型建构','实验探究','运算推理','规范表达']
LEVELS={'基础':1,'中档':2,'提升':3}
DETAIL_FIELDS={'sourcePage':'原卷页码','difficultyReason':'难度依据','abilityTask':'能力任务','conditions':'关键条件','challenge':'本题难点','studentAnswer':'原始作答','referenceAnswer':'参考结果','solution':'关键解法','scoringPoints':'评分点','scoringSource':'评分来源','mastery':'掌握状态','errorType':'错误分类','acceptance':'训练验收','questionText':'题干','teachingClass':'教学分类','teachingEvidence':'教学证据'}
CHECKS=[('identity','身份、试卷与材料来源对应'),('scores','分值、得失分与待核范围一致'),('overview','报告模块齐全且结论有证据'),('detail','详细题号覆盖完整（A类）'),('teaching','教学范围与覆盖证据（B类）'),('paper','纸质独立复做及变式记录（B类）'),('comparison','复做五模块与比较口径（B类）'),('plan','训练任务、责任与日期明确'),('layout','无重叠、截断、错名或乱码'),('archive','署名、复核与归档齐全')]
PLAN_FIELDS=['id','max','type','topic','ability','difficulty','core','method','criticalPoints','teachingClass','teachingEvidence','allowedMinutes','timeGoal','allowedTools','conditions','referenceAnswer','scoringPoints','scoringSource']
def string(v):return '' if v is None else str(v).strip()
def scored(q):return q.get('score') is not None and q.get('reviewed') is True
def number(v,allow_none=True):
    if v is None and allow_none:return None
    if isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v):raise ValueError('分数或时长须为有限数值')
    return v
def validate(d):
    if not isinstance(d,dict) or not isinstance(d.get('questions'),list):raise ValueError('报告需包含 questions 数组')
    d=copy.deepcopy(d);seen=set()
    if len(d['questions'])>300:raise ValueError('单份报告最多300个计分单元')
    for q in d['questions']:
        if not isinstance(q,dict):raise ValueError('逐题记录格式错误')
        q['id']=string(q.get('id')).replace('（','(').replace('）',')')
        if not q['id'] or q['id'] in seen:raise ValueError('题号不能为空或重复')
        seen.add(q['id']);m=number(q.get('max'),False);v=number(q.get('score'))
        if not 0<m<=1000 or v is not None and not 0<=v<=m:raise ValueError('题目满分须大于0，得分须在0与满分之间')
        if q.get('difficulty') not in LEVELS:raise ValueError('难度须为基础、中档或提升')
        if q.get('ability') not in ABILITIES:raise ValueError('主要能力维度不在标准范围内')
        for k in list(DETAIL_FIELDS)+['type','topic','evidence','cause','action','method','criticalPoints','allowedTools','priorityReason','digestEvidence','digestMastery','digestAction']:
            q[k]=string(q.get(k))[:12000]
        q['studentAnswer']=q['studentAnswer'] or q['evidence'];q['reviewed']=q.get('reviewed') is True
        q['core']=q.get('core') is True;q['target']=q.get('target') is True;q['timeGoal']=q.get('timeGoal') is True
        q['priority']=int(q.get('priority') or 0)
        q['retake']=clean_attempt(q.get('retake',{}),m)
        if q.get('allowedMinutes') is not None and number(q['allowedMinutes'])<0:raise ValueError('允许时长不能为负')
    # A whole question and its independently-scored subquestions cannot coexist.
    for qid in seen:
        if '(' not in qid and any(other.startswith(qid+'(') for other in seen):raise ValueError(f'第{qid}题与其小问重复计分，请保留一种粒度')
    scope=d.get('retakeScope')
    if scope:
        if not isinstance(scope,dict) or not isinstance(scope.get('ids'),list) or not isinstance(scope.get('snapshot'),list):raise ValueError('锁定题组记录不完整')
        ids=scope['ids'];snaps=scope['snapshot']
        if not ids or len(ids)!=len(set(ids)) or not set(ids)<=seen or len(snaps)!=len(ids) or {s.get('id') for s in snaps}!=set(ids):raise ValueError('锁定题组与题目快照不一致，请留痕重新确定范围')
    for k in ['student','studentId','grade','stage','exam','teacher','institution','summary','plan','followup','materialNotes','examDate','analysisDate','reviewer','reviewDate','deliveryDate','version','strengthText','weaknessText','directionText','retakeDate','retakeSummary','retakePlan','retakeStrength','retakeWeakness','retakeDirection','difficultyConclusion','scopeChangeReason']:
        d[k]=string(d.get(k))[:12000]
    d['stage']=d['stage'] or '高中';d['service']='B' if d.get('service')=='B' else 'A';d['schemaVersion']=2
    d['difficultyPoints']=[string(v) for v in (d.get('difficultyPoints') or [])][:3]
    d['difficultySources']=[string(v) for v in (d.get('difficultySources') or [])][:3]
    d['variants']=[dict(v,**clean_attempt(v,None)) for v in (d.get('variants') or [])]
    variant_ids=set()
    for v in d['variants']:
        v['id']=string(v.get('id'));v['method']=string(v.get('method'))
        if not v['id'] or v['id'] in variant_ids or not v['method']:raise ValueError('变式须有唯一题号和对应错因或核心方法')
        variant_ids.add(v['id'])
    d['companyChecks']=d.get('companyChecks') if isinstance(d.get('companyChecks'),dict) else {}
    # Migrate old manually edited summaries without retaining stale loss amounts.
    for row in d.pop('lossDigest',[]) or []:
        matches=[q for q in d['questions'] if q['topic']==row.get('topic')]
        if len(matches)==1:
            q=matches[0]
            for old,new in [('evidence','digestEvidence'),('mastery','digestMastery'),('action','digestAction')]:
                if not q[new] and row.get(old):q[new]=string(row[old])
    return d
def clean_attempt(a,maxscore):
    if not isinstance(a,dict):raise ValueError('复做记录须为对象')
    a=copy.deepcopy(a)
    for k in ['independent','resultCorrect','stepsCorrect','expressionComplete','conditionsMet']:
        if a.get(k) not in (None,True,False) or isinstance(a.get(k),(str,int)) and not isinstance(a.get(k),bool):raise ValueError('复做检查项必须为是、否或待核')
        a[k]=a.get(k)
    a['reviewed']=a.get('reviewed') is True;a['state']=a.get('state') or '未测'
    if a['state'] not in ['未测','已测','未作答','材料缺失']:raise ValueError('复做状态无效')
    for k in ['evidence','explanation','remainingCause','nextAction','studentAnswer','date','helpNote']:
        a[k]=string(a.get(k))[:12000]
    a['score']=number(a.get('score'))
    if a['score'] is not None and (a['score']<0 or maxscore is not None and a['score']>maxscore):raise ValueError('复做得分超出题目满分')
    for k in ['normYes','normTotal']:
        a[k]=a.get(k) or 0
        if isinstance(a[k],bool) or not isinstance(a[k],int) or a[k]<0:raise ValueError('规范项数量须为非负整数')
    if a['normYes']>a['normTotal']:raise ValueError('规范通过项不能多于适用项')
    a['minutes']=number(a.get('minutes'))
    if a['minutes'] is not None and a['minutes']<0:raise ValueError('用时不能为负')
    return a
def group(d,key):
    out={}
    for q in d['questions']:
        v=out.setdefault(q[key],[0,0,0]);v[0]+=q['max']
        if scored(q):v[1]+=q['score'];v[2]+=q['max']
    return out
def stats(d):return sum(q['max'] for q in d['questions']),sum(q['score'] for q in d['questions'] if scored(q)),sum(q['max'] for q in d['questions'] if scored(q))
def difficulty(d):
    total=stats(d)[0]
    avg=sum(q['max']*LEVELS[q['difficulty']] for q in d['questions'])/total if total else 1
    return {'weighted':avg,'normalized':(avg-1)/2,'label':'基础为主' if avg<1.5 else '中等' if avg<2 else '中上' if avg<2.5 else '较难'}
def abilities(d):
    g=group(d,'ability');result={}
    for k in ABILITIES:
        v=g.get(k,[0,0,0]);count=sum(1 for q in d['questions'] if q['ability']==k and scored(q));coverage=v[2]/v[0] if v[0] else 0
        eligible=count>=2 and coverage>=.5;value=v[1]/v[2]*100 if eligible else None
        result[k]={'score':v[1],'known':v[2],'total':v[0],'count':count,'coverage':coverage,'value':value,'band':'待评估' if value is None else '相对优势' if value>=80 else '继续提升' if value>=60 else '优先补强'}
    return result
def targets(d):
    scope=d.get('retakeScope') or {};ids=scope.get('ids')
    return [q for q in d['questions'] if q['id'] in ids] if ids is not None else [q for q in d['questions'] if q.get('target')]
def plan_snapshot(q):return {k:q.get(k) for k in PLAN_FIELDS}
def lock_scope(d):
    from datetime import datetime,timezone,timedelta
    qs=[q for q in d['questions'] if q.get('target')]
    if not qs:raise ValueError('请先选择复做目标题')
    for q in qs:
        if not q['criticalPoints'] or not q['method']:raise ValueError('锁定前须为每道目标题填写关键验收点和错因或核心方法')
        if q.get('teachingClass') not in ['已教方法','已教知识待迁移'] or not q.get('teachingEvidence'):raise ValueError('已教题复做范围须有已教方法或已教知识待迁移的分类及教学证据，未教和覆盖待核题不计入已教题验收')
        if q.get('timeGoal') and (q.get('allowedMinutes') is None or q['allowedMinutes']<=0):raise ValueError('设置限时目标时，必须在锁定前填写正数允许时长')
        if q.get('retake',{}).get('state','未测')!='未测':raise ValueError('应在复做前锁定题组，已有作答结果的题目不能事后锁定；请保留历史并建立新的复做批次')
    d=copy.deepcopy(d);d['retakeScope']={'ids':[q['id'] for q in qs],'snapshot':[plan_snapshot(q) for q in qs],'lockedAt':datetime.now(timezone(timedelta(hours=8))).isoformat(timespec='seconds')};return d
def attempt_result(a,plan=None):
    plan=plan or {}
    if a.get('state')=='未作答':return {'status':'未通过','reasons':['目标题未作答']}
    if a.get('state')!='已测':return {'status':'未测','reasons':[a.get('state') or '未测']}
    if not a.get('reviewed') or not a.get('evidence'):return {'status':'未测','reasons':['缺教师校核或独立答卷证据']}
    checks={'independent':'未独立完成','resultCorrect':'结果错误','stepsCorrect':'关键步骤未全部正确','expressionComplete':'必要表达不完整','conditionsMet':'未遵守事前约定'}
    missing=[label for k,label in checks.items() if a.get(k) is None]
    if missing:return {'status':'未测','reasons':['检查项待核：'+'、'.join(missing)]}
    reasons=[label for k,label in checks.items() if a.get(k) is False]
    if a.get('normTotal',0) and a.get('normYes',0)/a['normTotal']<.8:reasons.append('非关键规范未达80%')
    if plan.get('timeGoal'):
        if plan.get('allowedMinutes') is None or a.get('minutes') is None:return {'status':'未测','reasons':['限时目标或实际用时待补']}
        if a['minutes']>plan['allowedMinutes']:reasons.append('超出事前限时')
    return {'status':'未通过' if reasons else '通过','reasons':reasons}
def retake_summary(d):
    qs=targets(d);res={q['id']:attempt_result(q.get('retake',{}),q) for q in qs};total=sum(q['max'] for q in qs);passed=sum(q['max'] for q in qs if res[q['id']]['status']=='通过')
    methods=sorted({q.get('method') or q['topic'] for q in qs});variants=d.get('variants',[])
    method_results={m:any(v.get('method')==m and attempt_result(v)['status']=='通过' for v in variants) for m in methods}
    core=[q['id'] for q in qs if q.get('core')];missing=any(v['status']=='未测' for v in res.values())
    pending_variants=any(not ok and not any(v.get('method')==m and attempt_result(v)['status'] in ['通过','未通过'] for v in variants) for m,ok in method_results.items())
    passed_all=bool(qs) and passed/total>=.8 and all(res[k]['status']=='通过' for k in core) and all(method_results.values())
    scope=d.get('retakeScope') or {};changed=[]
    current={q['id']:q for q in d['questions']}
    for snap in scope.get('snapshot',[]):
        if snap.get('id') not in current or plan_snapshot(current[snap['id']])!=snap:changed.append(snap.get('id'))
    if changed or not scope or missing or pending_variants:status='未测或待完成'
    else:status='通过' if passed_all else '未通过'
    return {'status':status,'results':res,'total':total,'passedPoints':passed,'rate':passed/total if total else 0,'core':core,'corePassed':sum(res[k]['status']=='通过' for k in core),'methods':method_results,'scopeChanged':changed,'count':len(qs)}
def report_view(d,phase='first'):
    v=copy.deepcopy(d)
    if phase!='retake':return v
    qs=targets(d)
    if not qs:raise ValueError('尚未选择复做题组')
    v['questions']=copy.deepcopy(qs);v['reportKind']='retake';v['baseline']={'questions':copy.deepcopy(qs)}
    for q in v['questions']:
        a=q.get('retake',{});q.update(score=a.get('score'),reviewed=a.get('reviewed') is True and bool(a.get('evidence')) and a.get('independent') is True,studentAnswer=a.get('studentAnswer') or '复做作答待补',evidence=a.get('evidence') or '纸质证据待补',cause=a.get('remainingCause') or ('本题独立复做通过' if attempt_result(a,q)['status']=='通过' else '请结合复做原答核实当前错误'),action=a.get('nextAction') or '按未解决错因安排新题复测')
    # Scores and radar comparisons use the intersection of verified units.
    paired_before=copy.deepcopy(qs);paired_after=copy.deepcopy(v['questions']);common=[]
    for before,after in zip(paired_before,paired_after):
        both=scored(before) and scored(after)
        before['reviewed']=after['reviewed']=both
        if both:common.append((before,after))
    v['baseline']={'questions':paired_before};v['radarCurrent']={'questions':paired_after}
    v['pairedScores']={'before':sum(p['score'] for p,a in common),'after':sum(a['score'] for p,a in common),'max':sum(p['max'] for p,a in common),'count':len(common)}
    for key,source in [('summary','retakeSummary'),('plan','retakePlan'),('strengthText','retakeStrength'),('weaknessText','retakeWeakness'),('directionText','retakeDirection')]:v[key]=d.get(source,'')
    v.pop('lossDigest',None);v['retakeMetrics']=retake_summary(d)
    v['summary']=v['summary'] or f"本次复做{len(qs)}个计分单元；独立通过{sum(r['status']=='通过' for r in v['retakeMetrics']['results'].values())}项，后续围绕未解决问题继续训练。"
    chosen=sorted(qs,key=lambda q:(not q.get('core'),q['score']==q['max'] if scored(q) else False,-q.get('priority',0)))[:5]
    rows=[]
    for original in chosen:
        a=original['retake'];r=attempt_result(a,original);known=a.get('score') is not None and a.get('reviewed') and a.get('independent') is True and a.get('evidence')
        rows.append({'loss':f"{original['max']-a['score']:g}分" if known else '待核','topic':original['topic'],'evidence':f"第{original['id']}题："+(a.get('studentAnswer') or '独立作答待核'),'mastery':'本题复做通过' if r['status']=='通过' else a.get('remainingCause') or '、'.join(r['reasons']),'action':a.get('nextAction') or '同方法变式与后续抽查'})
    v['retakeRows']=rows
    ordered=[q for q in qs if q.get('difficultyReason')][:3]
    v['difficultyPoints']=[string(p) for p in d.get('retakeDifficultyPoints',[]) if string(p)] or [f"第{q['id']}题：{q['difficultyReason']}" for q in ordered]
    passes=[q['id'] for q in qs if v['retakeMetrics']['results'][q['id']]['status']=='通过']
    remaining=[q['id'] for q in qs if v['retakeMetrics']['results'][q['id']]['status']!='通过']
    v['strengthText']=v['strengthText'] or ('第'+ '、'.join(passes)+'题独立复做通过，关键步骤已落实。' if passes else '尚需通过独立作答补充掌握证据。')
    v['weaknessText']=v['weaknessText'] or ('第'+'、'.join(remaining)+'题需继续核实并训练。' if remaining else '当前复做原题均通过，继续检查同方法变式表现。')
    v['difficultyConclusion']='优先处理未通过项目' if remaining else '用变式检验方法迁移'
    return v
def audit(d,kind='first'):
    errors=[];warnings=[]
    def require(ok,msg):
        if not ok:errors.append(msg)
    for k,label in [('student','学生姓名'),('exam','考试名称'),('teacher','分析教师'),('analysisDate','分析日期'),('reviewer','复核人'),('reviewDate','复核日期'),('deliveryDate','交付日期')]:require(bool(d.get(k)),f'补充{label}')
    require(bool(d['questions']),'尚未录入题目')
    if kind in ['first','detail']:
        require(len([p for p in d.get('difficultyPoints',[]) if p])>=2,'整体难度至少填写两条学科依据')
        require(bool(d.get('plan') or d.get('directionText')),'补充学习方向或阶段训练安排')
    for q in d['questions']:
        require(q.get('reviewed'),f"第{q['id']}题未完成教师校核")
        needed=['type','topic','sourcePage','difficultyReason','abilityTask','conditions','challenge','studentAnswer','referenceAnswer','solution','scoringPoints','scoringSource','mastery','acceptance']
        for k in needed:require(bool(q.get(k)),f"第{q['id']}题缺{DETAIL_FIELDS.get(k,k)}")
        if q.get('score') is None:warnings.append(f"第{q['id']}题分数待核")
        if q.get('score') is None or q['score']<q['max']:
            for k,label in [('cause','原因与已会部分'),('action','对应训练'),('errorType','错误分类')]:require(bool(q.get(k)),f"第{q['id']}题缺{label}")
    if any(q['score'] is None for q in d['questions']):require(d.get('partialApproved') is True and bool(d.get('materialNotes')),'存在待核分数，需登记范围并由负责人确认阶段性交付')
    sources=d.get('difficultySources',[])
    if kind in ['first','detail']:
        require(len(sources)>=2 and all(sources[:2]),'至少两条难度依据需关联题号')
        ids={q['id'] for q in d['questions']}
        for source in sources:
            refs=[s.strip().replace('第','').replace('题','').replace('（','(').replace('）',')') for s in re.split('[,，、;； ]+',source) if s.strip()]
            require(all(r in ids for r in refs),'难度依据关联了不存在的题号：'+source)
    if d['service']=='B' and kind in ['paper','retake']:
        qs=targets(d);r=retake_summary(d);require(bool(d.get('retakeScope')),'复做题组未事前锁定');require(not r['scopeChanged'],'锁定后修改了目标题或验收条件，需留痕重新锁定')
        require(bool(d.get('retakeDate')),'补充复做日期')
        require(bool(qs),'尚未选择复做目标题')
        for q in qs:
            require(bool(q.get('teachingClass')),'第'+q['id']+'题教学分类待补')
            if q.get('teachingClass') in ['已教方法','已教知识待迁移']:require(bool(q.get('teachingEvidence')),'第'+q['id']+'题教学证据待补')
            a=q['retake'];require(bool(a.get('evidence')) and a.get('reviewed'),'第'+q['id']+'题缺纸质证据或复做校核')
            require(bool(a.get('explanation')),'第'+q['id']+'题讲解记录待补')
            if r['results'][q['id']]['status']!='通过':require(bool(a.get('nextAction')),'第'+q['id']+'题未通过或未测，需后续安排')
        if kind=='retake':
            require(bool(d.get('retakePlan') or d.get('retakeDirection')),'复做报告需单独填写下一阶段安排')
            require(bool(qs) and len(report_view(d,'retake').get('difficultyPoints',[]))>=2,'复做题组至少补充两条难度依据')
        for m,ok in r['methods'].items():
            rows=[v for v in d.get('variants',[]) if v.get('method')==m];require(bool(rows),'错因或方法“'+m+'”缺对应变式记录')
            for row in rows:require(bool(row.get('evidence')) and row.get('reviewed'),'变式 '+row.get('id','')+' 缺真实作答记录或校核')
        warnings.append('学生学习验收：'+r['status'])
    for key,label in CHECKS:
        excluded=['teaching','paper','comparison'] if d['service']=='A' else ['detail']
        if d['service']=='B' and kind=='first':excluded+=['teaching','paper','comparison']
        if d['service']=='B' and kind=='paper':excluded+=['comparison']
        applicable=key not in excluded
        if applicable:require(d['companyChecks'].get(key,{}).get('status')=='通过','人工验收未通过：'+label)
    return {'status':'退回修改' if errors else '合格','errors':errors,'warnings':warnings,'ability':abilities(d),'difficulty':difficulty(d),'retake':retake_summary(d) if d['service']=='B' else None}

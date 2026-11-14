"""Index-generated synthetic workload; declarations below are fixture decisions only."""
import copy
import hashlib
import answer_draft as ad
import argument_proposals as gp
import applicability_review as ar
import design_scenario as ds
import pattern_hypotheses as ph
import publication_context as pc
import reasoning_links as rl
import research_workflow as rw

QUESTION='Synthetic capacity question, not research advice.'
TOPIC='synthetic capacity'


def dimensions(n,k,c,s):
    if any(type(v) is not int or not 1<=v<=32 for v in (n,k,c,s)) or s>c:
        raise ValueError('runner dimensions require 1 <= N,K,C <= 32 and 1 <= S <= C; not product limits')


def build(n,k,c,s):
    dimensions(n,k,c,s)
    papers=[]
    for i in range(n):
        observations=[dict(method=f'Invented method {i}-{j}',condition='Invented condition only.',
             limitation='Synthetic record, no scientific claim.',locator=f'Section {j}',topic=TOPIC,
             evidence_quote=f'Invented sentence {i}-{j}.',claim_type='operator_interpretation') for j in range(k)]
        papers.append(dict(paper_id=f'synthetic-capacity-{i:04d}',author_id='synthetic-capacity',
             split='training',runtime_knowledge_eligible=True,authorized=True,
             source_sha256=hashlib.sha256(f'Invented source {i}'.encode()).hexdigest(),
             locator=f'Invented file {i}',kind='research',year=2000+i,topic=TOPIC,observations=observations))
    package=rw.build(dict(author_id='synthetic-capacity',version='1',build_id='synthetic-capacity',papers=papers))
    reference=dict(paper_id=papers[0]['paper_id'],observation_index=0,dimension=None)
    patterns=ph.template(package,'synthetic-operator')
    patterns['hypotheses']=[dict(pattern_id='synthetic-pattern',operator_hypothesis='Invented hypothesis.',
        scope_note='Synthetic fixture only.',support_refs=[reference],challenge_refs=[],
        alternative_explanation='Other interpretations remain possible.',falsification_check=None,uncertainty='Not assessed.')]
    context=ar.template(package,QUESTION,'Invented target.',TOPIC,2032,'synthetic-operator')
    links=rl.template(package,'synthetic-operator')
    proposal=ds.template(package,links,QUESTION,'synthetic-operator')
    draft=ad.template(package,QUESTION,'synthetic-operator')
    draft['claims']=[dict(claim_id=f'claim-{i}',text=f'Invented claim {i}.',claim_type='operator_synthesis',
                         uncertainty='Synthetic only.',citations=[dict(reference=reference,role='support')] if i==0 else []) for i in range(s+1)]
    review=ad.review_template(package,draft,'synthetic-reviewer')
    scope=gp.template(package,draft,'synthetic-operator',review)
    scope['selected_claim_ids']=[r['claim_id'] for r in draft['claims']]
    handoff=gp.prepare_handoff(package,draft,scope,review)
    response=gp.response_template(package,draft,scope,handoff,review)
    response['candidates']=[dict(premise_claim_ids=[f'claim-{i%s}'],conclusion_claim_id=f'claim-{i%s+1}',
        bridge_rationale=f'Invented candidate {i}.',assumptions=[],defeater=None) for i in range(c)]
    provenance=dict(provider_id='synthetic-no-provider',model_id='synthetic-no-model',run_id='synthetic-capacity',
                    operator_id='synthetic-operator',execution_location='unknown')
    bundle=gp.import_response(package,draft,scope,handoff,response,provenance,review)
    adoption=gp.review_template(package,draft,bundle,'synthetic-adopter',review)
    for i,decision in enumerate(adoption['decisions']):
        decision.update(decision='accept' if i<s else 'reject',review_note='Fixed synthetic fixture decision only.')
        if i<s:decision['reviewed_step']=dict(copy.deepcopy(response['candidates'][i]),step_id=f'step-{i}')
    argument=gp.export_reviewed(package,draft,bundle,adoption,review)
    relations=pc.template(package,'synthetic-operator')
    return [package,patterns,context,links,proposal,draft,argument,relations,'synthetic-pattern',review]

"""Regression checks for the editable plan, review guidance, handoff, and reset."""
from pathlib import Path
import sys, json, math, unittest
from unittest.mock import patch
from types import SimpleNamespace
ROOT=Path(__file__).resolve().parents[1]
APP=ROOT/'software/microfluidic-eis-agent'
sys.path.insert(0,str(APP))
from workflow_context import clean_plan, experiment_checklist, build_fit_lab_template, load_fit_lab_template_from_package
from microfluidic_agent import parse_requirement, build_design_package, generate_openai_design_package, model_impedance
from streamlit.testing.v1 import AppTest

class WorkflowTests(unittest.TestCase):
    def test_plan_roundtrip_and_unknowns(self):
        plan=clean_plan(dict(research_question='Question',planned_comparison='Matched groups',control_condition='Vehicle',baseline_plan='Before treatment',measurement_schedule='24 h, 48 h',measurement_settings='5 Hz to 100 kHz',export_plan='CSV and JSON',metadata_plan='Sample IDs and replicates'))
        req=parse_requirement('endothelial drug response',['iPSC-Endo'],['Test compound'],['EIS']);req.update(plan)
        package=build_design_package(req)
        package['requirement']['active_area_cm2']=0.45
        package['fit_lab_template']=build_fit_lab_template(package,0.45)
        loaded=load_fit_lab_template_from_package(json.loads(json.dumps(package)))
        self.assertEqual(loaded['control_condition'],'Vehicle')
        self.assertEqual(loaded['drugs'],['Test compound'])
        self.assertEqual(loaded['measurement_schedule'],'24 h, 48 h')
        self.assertEqual(loaded['active_area_cm2'],0.45)
        self.assertTrue(all(not x for x in loaded['sample_context'].values()))
        self.assertTrue(all(done for _,done in experiment_checklist(req['cells'],req['drugs'],req['electrical'],plan)))
        self.assertFalse(experiment_checklist([],[],[],{})[-1][1])
        self.assertTrue(all(not src['available'] for src in package['knowledge_base']))
        self.assertTrue(all(src['status']=='missing_file' for src in package['knowledge_base']))
        # Private reference PDFs are deliberately absent from the public package.

    def test_legacy_and_bad_imports(self):
        package=build_design_package(parse_requirement('MDCK',['MDCK'],[],['EIS']))
        legacy=load_fit_lab_template_from_package(package)
        self.assertIsNone(legacy['active_area_cm2'])
        for bad in (float('nan'),float('inf'),-1,0,'abc'):
            package['requirement']['active_area_cm2']=bad
            with self.assertRaises((ValueError,TypeError)):load_fit_lab_template_from_package(package)
        with self.assertRaises(ValueError):load_fit_lab_template_from_package({'selected_template':[], 'requirement':{}})

    def test_api_contract_with_stub(self):
        req=parse_requirement('endothelial',['iPSC-Endo'],['Test compound'],['EIS'])
        req.update(clean_plan({'control_condition':'vehicle','measurement_schedule':'proposed 24 h'}))
        captured={}
        def create(**kwargs):
            captured.update(kwargs)
            return SimpleNamespace(output_text=json.dumps({'assay_summary':{'agent_summary':'Draft'},'build_view':{},'operate_view':{},'analyze_view':{}}))
        with patch('microfluidic_agent.OpenAI', return_value=SimpleNamespace(responses=SimpleNamespace(create=create))):
            result=generate_openai_design_package(req,'test-only-placeholder')
        self.assertEqual(json.loads(captured['input'])['requirement']['control_condition'],'vehicle')
        self.assertEqual(result['workflow_status'],'draft awaiting researcher review')
        self.assertIn('pretreatment',captured['instructions'])
        self.assertEqual(result['requirement']['measurement_schedule'],'proposed 24 h')

    def test_workshop_user_flow(self):
        at=AppTest.from_file(str(APP/'streamlit_app.py'),default_timeout=50).run()
        self.assertFalse(at.exception)
        at.button(key='home_open_agent').click().run()
        self.assertFalse(at.exception)
        next(x for x in at.selectbox if x.label=='Assay preset').select('Endothelial drug-response barrier assay').run()
        self.assertEqual(at.text_input(key='control_condition').value,'Vehicle control')
        self.assertEqual(at.multiselect(key='drug_setup').value,['Test compound'])
        self.assertEqual(at.text_input(key='measurement_schedule').value,'')
        at.text_input(key='baseline_plan').input('Pretreatment after stabilization')
        at.text_input(key='measurement_schedule').input('baseline, 24 h, 48 h')
        at.text_input(key='active_area_cm2_text').input('0.45')
        at.text_input(key='export_plan').input('CSV and JSON')
        at.text_area(key='metadata_plan').input('Record sample ID, chip ID, settings, time point, condition and replicate')
        at.text_area(key='measurement_settings').input('5 Hz to 100 kHz; 10 mV rms')
        at.run()
        next(b for b in at.button if b.label=='Generate Workflow Draft').click().run()
        self.assertFalse(at.exception)
        self.assertTrue(at.session_state['generated'])
        package=at.session_state['package']
        self.assertEqual(package['fit_lab_template']['measurement_schedule'],'baseline, 24 h, 48 h')
        self.assertTrue(any('draft awaiting researcher review' in el.value for el in at.info))
        for view in ('build','operate','analyze','export'):
            at.button(key='output_nav_'+view).click().run()
            self.assertFalse(at.exception,view)
        next(b for b in at.button if b.label=='Open Workflow in Fit Lab').click().run()
        self.assertFalse(at.exception)
        self.assertEqual(at.session_state['fit_lab_design_template']['active_area_cm2'],0.45)
        self.assertEqual(at.session_state['app_page'],'fitlab')
        # Browser tests cover returning from Fit Lab to Edit Input. AppTest retains
        # stale button triggers across the st.rerun page transition, so reset is
        # exercised in a fresh session with only the input page's live widgets.
        at=AppTest.from_file(str(APP/'streamlit_app.py'),default_timeout=50).run()
        at.button(key='home_open_agent').click().run()
        next(x for x in at.selectbox if x.label=='Assay preset').select('Endothelial drug-response barrier assay').run()
        next(b for b in at.button if b.label=='Reset').click().run()
        self.assertFalse(at.exception)
        self.assertEqual(next(x for x in at.selectbox if x.label=='Assay preset').value,'Custom')
        self.assertEqual(at.text_input(key='control_condition').value,'')
        self.assertEqual(at.text_area(key='research_question').value,'')
        for preset in ('MDCK apical-basal transport assay','Barrier maturation time-course'):
            next(x for x in at.selectbox if x.label=='Assay preset').select(preset).run()
            self.assertFalse(at.exception)
            self.assertTrue(at.text_area(key='research_question').value)
            self.assertNotIn('Vehicle control',at.multiselect(key='drug_setup').value)
        # Invalid area must show an actionable error without crashing.
        at.text_input(key='active_area_cm2_text').input('nan').run()
        next(b for b in at.button if b.label=='Generate Workflow Draft').click().run()
        self.assertTrue(at.error)
        self.assertFalse(at.exception)

if __name__=='__main__':unittest.main(verbosity=2)

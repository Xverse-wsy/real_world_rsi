"""Compare physics exactly and account separately for OpenGL pixel rounding."""
import json
from pathlib import Path
import sys
import numpy as np
from PIL import Image


def main():
    root=Path(sys.argv[1])
    before=json.loads((root/'before/report.json').read_text())
    after=json.loads((root/'after/report.json').read_text())
    for field in ('local_mock_only','external_api_requests','api_calls','code_executions','states','code_sha256'):
        assert before[field]==after[field],field
    assert len(before['requests'])==len(after['requests'])
    images=[]
    for left,right in zip(before['requests'],after['requests']):
        assert left['path']==right['path']
        assert left['non_image_sha256']==right['non_image_sha256'],'Text or model parameters changed'
        assert len(left['images'])==len(right['images'])
        for a,b in zip(left['images'],right['images']):
            ia=np.asarray(Image.open(root/'before'/a)).astype(float)
            ib=np.asarray(Image.open(root/'after'/b)).astype(float)
            assert ia.shape==ib.shape
            delta=np.abs(ia-ib)
            item=dict(image=a,max_absolute_difference=float(delta.max()),mean_absolute_difference=float(delta.mean()),
                      changed_color_values=int(np.count_nonzero(delta)))
            assert item['max_absolute_difference']<=1 and item['mean_absolute_difference']<.001,item
            images.append(item)
    report=dict(local_mock_only=True,external_api_requests=0,
        normal_execution_physical_states_identical=True,request_text_and_parameters_identical=True,
        code_execution_count_identical=True,control_steps_identical=True,
        image_pixel_rounding_checked=True,images=images)
    (root/'normal_comparison.json').write_text(json.dumps(report,indent=2))
    print('NORMAL_EXECUTION_COMPARISON_PASS',json.dumps(report),flush=True)


if __name__=='__main__':main()

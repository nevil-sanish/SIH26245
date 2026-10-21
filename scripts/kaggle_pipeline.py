# SAKSHI measured run as a Kaggle kernel (GPU + internet on; attach the sakshi-finetune kernel as input):
# fine-tune output -> scripts/gpu_runs.sh -> /kaggle/working/results (fetch with `kaggle kernels output`).
import glob, os, subprocess, sys
heads = glob.glob("/kaggle/input/**/rfdetr_nano_head.onnx", recursive=True)
print("head ONNX found:", heads, flush=True)
if not heads:
    sys.exit("fine-tune output not attached")
env = dict(os.environ, ONNX_DIR=os.path.dirname(heads[0]), RESULTS="/kaggle/working/results")
R = "/tmp/sakshi"
subprocess.run(f"rm -rf {R} && git clone -q --depth 1 https://github.com/nevil-sanish/SIH26245.git {R}", shell=True, check=True)
r = subprocess.run(f"bash scripts/gpu_runs.sh 2>&1 | tee /kaggle/working/gpu_runs.log", shell=True, cwd=R, env=env,
                   executable="/bin/bash")
print("exit", r.returncode)

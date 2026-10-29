# A800 LIBERO environment — 2026-10-14

Repository: /home/wenchaoxu/wsy/vla-recovery-posttrain-loop/cap-x
Screen: capx_libero_setup
Virtual environment: .venv-libero (Python 3.12.14)
Torch: 2.9.1+cu128, CUDA tensor computation verified on physical GPU 4.
Activate from the repository root:
    source .setup/activate.sh
Attach to the retained screen:
    screen -r capx_libero_setup

Installed:
- LIBERO-PRO and its Robosuite 1.4 fork
- capx, SAM3 code, Contact-GraspNet code, PyRoKi/jaxls
- LIBERO assets, BDDL files and initial states; Panda URDF/mesh resources
- Node 22.14.0 local to .setup/node22; Web UI production build

Verification passed:
- CUDA tensor computation
- LIBERO spatial task 0 reset, five simulation steps and RGB rendering (128x128)
- cap-x LIBERO wrapper reset and Python open_gripper() execution (sandbox_rc=0)
- SAM3 / Contact-GraspNet / PyRoKi / Web backend imports
- OpenCV color conversion and Decord import
- Web API GET /api/configs returned HTTP 200
- launch.py --help
Logs: verify.log, packages.log, pip_check.txt, web.log, node.log.

Hugging Face endpoint: https://hf-mirror.com
Cache: .cache/huggingface
HF_HUB_OFFLINE=1 and TRANSFORMERS_OFFLINE=1 remain set during setup.
SAM3 checkpoint downloaded from ModelScope facebook/sam3 on 2026-10-14.
No LLM checkpoint downloaded.
Contact-GraspNet's source archive included checkpoints; retained per user instruction.
SAM3 offline GPU model loading verified; end-to-end coding agent evaluation awaits LLM endpoint selection.

LIBERO config is project-local in .setup/libero/config.yaml.
CUDA_VISIBLE_DEVICES=4 and MUJOCO_EGL_DEVICE_ID=4.
The fork requires the physical EGL GPU ID, not remapped CUDA index 0.
PyRoKi uses CPU JAX in this install, as in the project's minimal profile.

Dependency metadata caveats (runtime checks above pass):
- pyrender pins PyOpenGL 3.1.0; repository explicitly overrides to 3.1.6.
- OpenCV 4.12 wheel declares NumPy>=2; repository overrides NumPy to 1.26.4.
- Robosuite declares opencv-python; repository disables that package in favor of headless.
- Decord's wheel has a stale cp36 tag internally; its runtime import works on Python 3.12.
- Generic Robosuite 1.5 modules are skipped with a traceback on startup under the LIBERO fork.
This environment targets LIBERO, not BEHAVIOR or RL training.

GitHub Git clones failed with TLS errors. Submodule sources were obtained from codeload
archives at the exact gitlink commits; .capx_archive_commit records each source version.
PyRoKi/jaxls archives use exact uv.lock commits in .setup/vendor.
Python versions were exported from uv.lock; install_packages.sh installs that complete
list with --no-deps because resolving source metadata otherwise refetches Git dependencies.
Torch/CUDA wheels were copied independently from matching installed packages in nanojev,
only after verifying their RECORD hashes; reuse.log records the result.
Large downloaded wheels were verified against uv.lock SHA256.
Original project pyproject.toml and uv.lock were not changed.

To repeat runtime verification:
    bash .setup/verify.sh

## SAM3 checkpoint

Source: https://modelscope.cn/models/facebook/sam3
Path: .cache/models/sam3/sam3.pt (symlink to project HF cache; no duplicate checkpoint).
Size: 3,450,062,241 bytes.
SHA256: 9999e2341ceef5e136daa386eecb55cb414446a00ac2b55eb2dfd2f7c3cf8c9e
Matches the SHA256 published for facebook/sam3 on Hugging Face.
Both config.json and sam3.pt resolve through HF cache with local_files_only=True.
GPU model construction and checkpoint loading passed with instance interactivity enabled.
Verification log: .setup/verify_sam3.log.
Download log: .setup/download_sam3_modelscope.log.
Exact source/cache details: .setup/sam3_download.json.
HF gated account restrictions remain, but local SAM3 startup no longer needs online access.


Molmo2-8B enabled via ModelScope; all 8 weight shards match official HF SHA256.
GPU 3, localhost:8122, screen capx_molmo_server; restart with bash .setup/start_molmo.sh.
Server log: .setup/molmo_server.log; actual cap-x point client verified on a LIBERO frame.
run_openai_libero.py now enables visual feedback, registers the exact model ID, includes
the authoritative task completion flag in multi-turn prompts, and uses timestamped output folders.

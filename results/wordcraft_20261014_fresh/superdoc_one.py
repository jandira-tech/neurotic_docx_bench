"""One SuperDoc compare per process: superdoc_one.py BASE NEXT OUT (run in bin/superdoc-venv).

Calls the bench's own superdoc_gen.generate_one (capture -> compare -> apply tracked -> save),
loaded by file path so nothing else from the bench package is imported into this venv."""
import asyncio,importlib.util,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('superdoc_gen',ROOT/'src/neurotic_docx_bench/superdoc_gen.py');gen=importlib.util.module_from_spec(spec);sys.modules['superdoc_gen']=gen;spec.loader.exec_module(gen)
from superdoc import AsyncSuperDocClient
async def main(base,nxt,out):
 async with AsyncSuperDocClient(user={'name':'superdoc','email':'bench@example.com'}) as client:
  await gen.generate_one(client,Path(base),Path(nxt),Path(out),0)
if __name__=='__main__':asyncio.run(main(*sys.argv[1:4]))

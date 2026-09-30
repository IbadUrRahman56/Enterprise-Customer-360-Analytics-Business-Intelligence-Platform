"""Record only this project's installed dependency closure, excluding runtime tools."""
from importlib.metadata import distribution
from pathlib import Path
from packaging.requirements import Requirement
from packaging.utils import canonicalize_name

pending=[Requirement(line).name for line in Path("requirements.txt").read_text().splitlines() if line and not line.startswith("#")]
versions={}
while pending:
    name=canonicalize_name(pending.pop())
    if name in versions: continue
    dist=distribution(name)
    versions[name]=dist.version
    for value in dist.requires or []:
        requirement=Requirement(value)
        if requirement.marker is None or requirement.marker.evaluate({"extra":""}): pending.append(requirement.name)
Path("requirements-lock.txt").write_text("# Tested Python 3.12 environment. Windows dependency closure.\n"+"\n".join(f"{name}=={version}" for name,version in sorted(versions.items()))+"\n")

from pathlib import Path
from schemas import Document
from charset_normalizer import from_path

def load_local_file(path: Path) -> Document:
    encoding = from_path(path).best().encoding

    print(f"""
load_local_file
 - path: {str(path)}
 - encoding: {encoding}
""")
    
    
    text = path.read_text(encoding=encoding)

    return Document(
        title=path.stem,
        content=text,
        source="local",
        url=str(path)
    )
class Document:

    def __init__(
        self,
        title, content, source, url
    ):
        self.title = title
        self.content = content
        self.source = source
        self.url = url

    def __repr__(self):
        return f"""
제목: {self.title}
내용: {self.content}
소스: {self.source}
URL: {self.url}
"""

    def __str__(self):
        return f"""
제목: {self.title}
내용: {self.content}
소스: {self.source}
URL: {self.url}
"""

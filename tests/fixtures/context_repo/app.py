"""Demo FastAPI application."""

from fastapi import FastAPI

app = FastAPI()

# padding so snippets cannot equal the whole file
# line
# line
# line
# line
# line
# line
# line
# line


@app.get("/health")
def health():
    return {"ok": True}


# more padding after the export
# line
# line
# line
# line
# line
# line

from mangum import Mangum

from src.app.api import app

# Lambda API runner
handler = Mangum(app)


# Local API runner
def run_local():
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8127, reload=True)


if __name__ == "__main__":
    run_local()

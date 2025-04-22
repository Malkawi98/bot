# --------- requirements ---------

FROM python:3.11 as requirements-stage

WORKDIR /tmp

COPY ./pyproject.toml /tmp/

# If you have a requirements.txt, uncomment the next two lines:
# COPY ./requirements.txt /tmp/
# RUN pip install --no-cache-dir --upgrade -r /tmp/requirements.txt

# --------- final image build ---------
FROM python:3.11

WORKDIR /code

ENV PYTHONPATH=/code

COPY --from=requirements-stage /tmp/pyproject.toml /code/pyproject.toml
# If you have a requirements.txt, uncomment the next line:
# COPY --from=requirements-stage /tmp/requirements.txt /code/requirements.txt

RUN pip install uv && uv pip install --system --upgrade .

RUN ls -lha ./src
COPY ./src/app /code/app

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

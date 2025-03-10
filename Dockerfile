FROM public.ecr.aws/lambda/python:3.13

# Define working directory
ARG WORKING_DIR=${LAMBDA_TASK_ROOT}

# Set environment variables
ARG PROJECT_KEY
ENV PROJECT_KEY=${PROJECT_KEY}

ARG ENV
ENV ENV=${ENV}


ENV PIP_NO_CACHE_DIR=off \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    POETRY_VERSION=2.1.1

# Update pip
RUN python3 -m pip install --upgrade pip

# Set the working directory to the root of the project.
WORKDIR ${WORKING_DIR}

# Install poetry
RUN pip install "poetry==$POETRY_VERSION"

# Copy only poetry.lock & pyproject.toml to cache them in docker layer
COPY poetry.lock pyproject.toml ${WORKING_DIR}/

# # Setup SSH for private repos
# ARG SSH_PRIVATE_KEY
# RUN yum install -y openssh-clients

# RUN mkdir -p /root/.ssh/ \
#     && touch /root/.ssh/known_hosts \
#     && ssh-keyscan bitbucket.org >> /root/.ssh/known_hosts \
#     && echo "${SSH_PRIVATE_KEY}" > /root/.ssh/id_rsa \
#     && chmod 600 /root/.ssh/id_rsa 

# Install dependencies
RUN poetry config virtualenvs.create false \
    && poetry install --only main --no-interaction --no-ansi --no-root

RUN curl -O https://lambda-insights-extension.s3-ap-northeast-1.amazonaws.com/amazon_linux/lambda-insights-extension.rpm && \
    rpm -U lambda-insights-extension.rpm && \
    rm -f lambda-insights-extension.rpm

# Copy the code to the function directory
COPY . ./

CMD ["main.handler"]

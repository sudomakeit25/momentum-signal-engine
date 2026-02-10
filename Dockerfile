FROM public.ecr.aws/lambda/python:3.11

# Install dependencies
COPY requirements.txt ${LAMBDA_TASK_ROOT}/
RUN pip install --no-cache-dir -r ${LAMBDA_TASK_ROOT}/requirements.txt

# Copy application code
COPY config/ ${LAMBDA_TASK_ROOT}/config/
COPY src/ ${LAMBDA_TASK_ROOT}/src/

# Default handler — overridden per function in template.yaml
CMD ["src.lambda_handler.handler"]

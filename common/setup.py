from setuptools import setup, find_packages

setup(
    name="bookstore-common",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "Django>=4.0",
        "djangorestframework>=3.14",
        "PyJWT>=2.8.0",
        "httpx>=0.24.0",
        "redis>=4.0",
        "pika>=1.3.2",
        "opentelemetry-api>=1.20.0",
        "opentelemetry-sdk>=1.20.0",
        "opentelemetry-exporter-otlp>=1.20.0",
        "opentelemetry-instrumentation-django>=0.41b0",
        "opentelemetry-instrumentation-httpx>=0.41b0",
        "opentelemetry-instrumentation-pika>=0.41b0",
    ],
)

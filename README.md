# workflow-executor

## Installation

## Development

```console
mamba env create -f environment.yml
```

Activate the environment:

```console
conda activate env_workflow_executor
```

Install the CLI's:

```console
python setup.py install
```

Run the server:

```console
workflow-executor-server
```

Run the client:

```console
workflow-executor --help
```

## Setting up the environment

### kubeconfig

Set the `KUBECONFIG` environment variable access the k8s cluster

### STORAGE_CLASS

**Mandatory**

Set the `STORAGE_CLASS` environment variable
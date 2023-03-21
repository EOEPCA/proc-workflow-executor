
environment {
    PATH = "$WORKSPACE/conda/bin:$PATH"
    CONDA_UPLOAD_TOKEN = credentials('workflow-executor')
  }

pipeline {
    agent {
        docker { image 'docker.terradue.com/conda-build:latest' }
    }
    stages {
        stage('Test') {
            steps {
                sh '''#!/usr/bin/env bash
                conda build --version
                conda --version
                mamba clean -a -y 
                '''
            }
        }
        stage('Build') {
            steps {
                sh '''#!/usr/bin/env bash
                mkdir -p /home/jovyan/conda-bld/work
                cd $WORKSPACE
                conda config --add channels eoepca
                conda config --add channels "eoepca/label/dev"
                mamba build .
                '''
            }
        }
        stage('Deploy') {            
            steps { 
                withCredentials([string(credentialsId: 'eoepca-conda', variable: 'ANACONDA_API_TOKEN')]) {
                sh '''#!/usr/bin/env bash
                export PACKAGENAME=workflow-executor
                label=dev
                if [ "$GIT_BRANCH" = "master" ]; then label=main; fi
                anaconda upload --no-progress --force --user eoepca --label $label /srv/conda/envs/env_conda/conda-bld/*/$PACKAGENAME-*.tar.bz2
                '''}
            }
        }
    }
}
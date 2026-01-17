# Lacan 2

Este repositório contém a minha solução para o desafio técnico proposto pela FluxLab AI. O esqueleto inicial do código é portanto de autoria deles.

## Como rodar o projeto

Primeiro, é necessário instalar o [Conda](https://docs.conda.io/projects/conda/en/latest/user-guide/install/index.html) (Miniconda ou Anaconda), e então inicializar o ambiente virtual do Python e instalar todas as dependências com os seguintes comandos:

``` Bash
conda env create -f environment.yml

conda activate case_psicanalise
```

Com isso, basta executar o arquivo `pipeline.py`

```
python3 pipeline.py
```

## Escolha de prompts

Existem 3 prompts na pasta `prompts/`, o que será utilizado por padrão é o `prompt_v2`. Contudo, é possível escolher o prompt que será usado com flags (`-v1` e `-v0`) passadas por linha de comando na execução do script:

``` bash
# Executa o programa com o prompt_v1
python3 pipeline.py -v1

# Executa o programa com o prompt_v0
python3 pipeline.py -v0
```

## Como funciona o pipeline

## Como interpretar os resultados

## Modo interativo

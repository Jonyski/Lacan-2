from __future__ import annotations

import argparse
import json
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, Tuple, TypedDict

from dotenv import load_dotenv
from google import genai
from google.genai import types

from extra.interactive_mode import run_interactive_mode
from extra.resultpdf import create_clinical_pdf
from extra.visual_report import generate_infographic

# Imports obrigatórios para o novo escopo
try:
    from langgraph.graph import END, StateGraph
    from pydantic import BaseModel, Field, ValidationError
except ImportError:
    raise ImportError("Dependências ausentes. Instale: pip install pydantic langgraph")

# ===== INICIALIZAÇÕES GLOBAIS =====
load_dotenv()
BASE_DIR = Path(__file__).parent
INPUT_DIR = BASE_DIR / "data" / "input"
PROMPTS_DIR = BASE_DIR / "prompts"
OUT_PATH = BASE_DIR / "results.json"
API_KEY = os.getenv("GOOGLE_API_KEY")

if not API_KEY:
    raise ValueError("ERRO: GOOGLE_API_KEY não encontrada no .env")

# Cliente genai para acessar a API do Google e utilizar o Gemini
GENAI_CLIENT = genai.Client(api_key=API_KEY)

# =========================
# 1. Pydantic Schemas (Structured Output)
# =========================

RiskLevel = Literal["baixo", "médio", "alto"]


class RiskAssessment(BaseModel):
    level: RiskLevel
    signals: List[str] = Field(
        description="Sinais observados que indicam o nível de risco"
    )


class ClinicalReport(BaseModel):
    required: bool
    summary: str = Field(description="Resumo do laudo caso necessário")


class ClinicalOutput(BaseModel):
    """
    Schema principal que representa a análise clínica completa.
    Substitui a validação manual de dicionários.
    """

    analysis: str = Field(description="Análise clínica estruturada")
    themes: List[str] = Field(min_length=3, max_length=6)
    signifiers: List[str] = Field(min_length=3, max_length=8)
    hypotheses: List[str] = Field(min_length=2, max_length=4)
    questions: List[str] = Field(min_length=3, max_length=6)

    risk_assessment: RiskAssessment
    clinical_report: ClinicalReport


# =========================
# 2. State Definition
# =========================


class ClinicalState(TypedDict):
    filename: str
    input_text: str
    prompt_version: str

    # Resposta crua do modelo (string JSON)
    raw_response: Optional[str]

    # Objeto validado pelo Pydantic
    parsed_output: Optional[ClinicalOutput]

    # Lista de erros (parsing ou validação)
    errors: List[str]

    # Conta o número de tentativas falhas de gerar uma análise válida
    retry_count: int


# =========================
# 3. IO / Prompt Helpers
# =========================


def load_prompt(prompt_version: str) -> str:
    path = PROMPTS_DIR / f"prompt_{prompt_version}.txt"
    if not path.exists():
        # Fallback para teste se arquivo não existir
        return "Faça uma análise psicanalítica do texto: {INPUT}"
    return path.read_text(encoding="utf-8")


def read_inputs(input_dir: Path) -> List[Tuple[str, str]]:
    """
    Lê arquivos .txt. Retorna [(filename, content), ...]
    """
    # Se o diretório não existe, notificamos e erro e retornamos
    if not input_dir.exists():
        print(f"Warning: Directory {input_dir} not found.")
        return []

    inputs = []
    # Itera sobre todos os arquivos .txt no diretório
    for file_path in input_dir.glob("*.txt"):
        try:
            content = file_path.read_text(encoding="utf-8")
            inputs.append((file_path.name, content))
        except Exception as e:
            print(f"Error reading file {file_path.name}: {e}")

    return inputs


# =========================
# 4. Model Call
# =========================


def call_model(prompt_text: str) -> str:
    """
    Chama o modelo Gemini 3 Flash via API oficial.
    """
    try:
        response = GENAI_CLIENT.models.generate_content(
            model="gemini-3-flash-preview",
            contents=prompt_text,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.5,
                # Passar o schema Pydantic direto aqui melhora a precisão
                response_schema=ClinicalOutput,
                # É necessário desativar algumas barreiras de segurança,
                # pois os prompts podem conter temas sensíveis
                safety_settings=[
                    types.SafetySetting(
                        category="HARM_CATEGORY_DANGEROUS_CONTENT",
                        threshold="BLOCK_NONE",
                    ),
                    types.SafetySetting(
                        category="HARM_CATEGORY_HARASSMENT", threshold="BLOCK_NONE"
                    ),
                    types.SafetySetting(
                        category="HARM_CATEGORY_HATE_SPEECH", threshold="BLOCK_NONE"
                    ),
                    types.SafetySetting(
                        category="HARM_CATEGORY_SEXUALLY_EXPLICIT",
                        threshold="BLOCK_NONE",
                    ),
                    types.SafetySetting(
                        category="HARM_CATEGORY_CIVIC_INTEGRITY", threshold="BLOCK_NONE"
                    ),
                ],
            ),
        )

        return response.text
    except Exception as e:
        # Repassa o erro para ser capturado no generation_node
        raise RuntimeError(f"Error in the Google API: {str(e)}")


# =========================
# 5. LangGraph Nodes
# =========================


def generation_node(state: ClinicalState) -> ClinicalState:
    """
    Nó de Geração: Monta prompt e chama o modelo.
    """
    print(f"--- Node: Generation ({state['filename']}) ---")

    # Carrega o template do prompt baseado na versão do estado
    prompt_template = load_prompt(state["prompt_version"])
    # Injeta o texto de entrada no placeholder {INPUT} do prompt
    full_prompt = prompt_template.replace("{INPUT}", state["input_text"])

    try:
        # Chama o modelo (API do Gemini)
        response_str = call_model(full_prompt)
        # Retorna a atualização do estado com a string JSON crua
        state["raw_response"] = response_str
        return state
    except Exception as e:
        state["errors"] = [f"Error in generation node: {str(e)}"]
        return state


def clean_json_string(raw_str: str) -> str:
    """
    Remove delimitadores de markdown se existirem.
    """
    if "```" in raw_str:
        # Remove a primeira linha ```json e a última ```
        pattern = r"```json\s*(.*?)\s*```"
        match = re.search(pattern, raw_str, re.DOTALL)
        if match:
            return match.group(1)
        # Fallback simples se não achar o padrão exato
        return raw_str.replace("```json", "").replace("```", "").strip()
    return raw_str


def validation_node(state: ClinicalState) -> ClinicalState:
    """
    Nó de Validação: Usa Pydantic para validar o JSON cru.
    """
    print(f"--- Node: Validation ({state['filename']})---")

    raw = clean_json_string(state.get("raw_response") or "")
    errors = []
    parsed_obj = None

    try:
        # Validando o output de acordo com o formato e regras do Pydantic
        parsed_obj = ClinicalOutput.model_validate_json(raw)
    except ValidationError as e:
        # Captura erros de validação estrutural
        # (ex: lista muito curta, tipo errado)
        errors = [
            f"Validation Error: {err['msg']} at {err['loc']}" for err in e.errors()
        ]
    except json.JSONDecodeError as e:
        errors = [f"JSON Parse Error: {str(e)}"]
    except Exception as e:
        errors = [f"Unknown Error: {str(e)}"]

    state["parsed_output"] = parsed_obj
    state["errors"] = errors

    if errors:
        print(f"   [!] Failure in validation: {len(errors)} errors found.")

    return state


def should_correct(state: ClinicalState) -> Literal["correction", "end"]:
    errors = state.get("errors", [])
    retries = state.get("retry_count", 0)
    MAX_RETRIES = 3

    # Se tem erros e ainda temos tentativas sobrando -> Corrige
    if errors and retries < MAX_RETRIES:
        return "correction"

    # Se não, encerra o fluxo
    return "end"


def correction_node(state: ClinicalState) -> ClinicalState:
    print(f"--- [Node] Correction: Trying to fix error in {state['filename']} ---")

    # Recupera o que foi gerado errado e o erro
    wrong_output = state.get("raw_response", "")
    error_msgs = "\n".join(state.get("errors", []))
    # Incrementa o contador de retentativas
    state["retry_count"] = state.get("retry_count", 0) + 1

    # Prompt de Correção
    correction_prompt = f"""
    VOCÊ COMETEU UM ERRO NA GERAÇÃO ANTERIOR.
    
    TEXTO ORIGINAL:
    {state['input_text']}
    
    SUA SAÍDA ANTERIOR (ERRADA):
    {wrong_output}
    
    ERROS ENCONTRADOS PELO VALIDADOR:
    {error_msgs}
    
    TAREFA:
    Gere novamente o JSON corrigindo APENAS os erros apontados.
    Mantenha o formato estritamente JSON compatível.
    """

    try:
        new_resp = call_model(correction_prompt)
        state["raw_response"] = new_resp
        # Limpa os erros antigos para dar chance à nova validação
        state["errors"] = []
    except Exception as e:
        state["errors"].append(f"Erro na correção: {str(e)}")

    return state


# =========================
# 6. Graph Construction
# =========================


def build_graph() -> StateGraph:
    workflow = StateGraph(ClinicalState)

    # Adiciona nós
    workflow.add_node("generator", generation_node)
    workflow.add_node("validator", validation_node)
    workflow.add_node("correction", correction_node)

    # Fluxo linear inicial
    workflow.set_entry_point("generator")
    workflow.add_edge("generator", "validator")
    # Fluxo condicional para a correção de erros
    workflow.add_conditional_edges(
        "validator",
        should_correct,
        {
            "correction": "correction",
            "end": END,
        },
    )
    workflow.add_edge("correction", "validator")

    return workflow.compile()


def save_results(payload: Dict[str, Any], path: Path) -> None:
    # Converte o objeto Pydantic para dict antes de salvar, se existir
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


# =========================
# 7. Main Execution
# =========================


def main():
    # 1. Lê argumentos da linha de comando
    parser = argparse.ArgumentParser(description="Pipeline de Análise Clínica com IA")
    # Adiciona a flag -v1 para utilizar o prompt V1 ao invés do V2
    parser.add_argument(
        "-v1",
        action="store_true",
        help="Usa o Prompt V1 (Básico) ao invés do V2 (Estruturado)",
    )
    # Adiciona a flag -v0 para utilizar o prompt V0 ao invés do V2
    parser.add_argument(
        "-v0", action="store_true", help="Usa o Prompt V0 (Minimalista/Stress Test)"
    )
    # Adiciona a flag -i para utilizar o modo interativo ao invés de "batch"
    parser.add_argument(
        "-i", "--interactive", action="store_true", help="Modo Chatbot Interativo"
    )
    args = parser.parse_args()

    # Escolha de versão do prompt
    prompt_version = "v2"
    if args.v1:
        prompt_version = "v1"
    elif args.v0:
        prompt_version = "v0"

    # 2. Setup do Grafo
    app = build_graph()

    print(f"Iniciando Pipeline (LangGraph + Pydantic) - Prompt {prompt_version}...\n")

    if args.interactive:
        run_interactive_mode(app, prompt_version)
    else:
        # 3. Leitura dos arquivos de input
        items = read_inputs(INPUT_DIR)
        if not items:
            print("No files found in data/input. Terminating...")
            return

        results = []
        ok_count = 0

        for fname, text in items:
            # Estado Inicial
            initial_state: ClinicalState = {
                "filename": fname,
                "input_text": text,
                "prompt_version": prompt_version,
                "raw_response": None,
                "parsed_output": None,
                "errors": [],
                "retry_count": 0,
            }

            try:
                # Invoca o grafo
                final_state = app.invoke(initial_state)
                output_data = final_state["parsed_output"]
                errors = final_state["errors"]
                # Sucesso se temos objeto validado e zero erro
                is_ok = (output_data is not None) and (len(errors) == 0)
                if is_ok:
                    ok_count += 1
                    # Converter modelo Pydantic para dict para salvar no JSON final
                    output_dict = output_data.model_dump()

                    # Geração de output em PDF para facilitar a leitura humana
                    pdf_dir = BASE_DIR / "data" / "output"
                    try:
                        pdf_path = create_clinical_pdf(output_dict, fname, pdf_dir)
                        print(f"Result PDF created: {pdf_path.name}")
                    except Exception as e:
                        print(f"Error creating result PDF: {e}")
                else:
                    output_dict = None

                results.append(
                    {
                        "file": fname,
                        "ok": is_ok,
                        "errors": errors,
                        "output": output_dict,
                    }
                )
            except Exception as e:
                results.append(
                    {
                        "file": fname,
                        "ok": False,
                        "errors": [f"Runtime Error: {e}"],
                        "output": None,
                    }
                )

        # 4. Consolidação
        payload = {
            "prompt_version": prompt_version,
            "total": len(results),
            "ok": ok_count,
            "failed": len(results) - ok_count,
            "results": results,
        }

        save_results(payload, OUT_PATH)
        print(f"Processamento concluído. Salvo em {OUT_PATH}")
        print(f"Sucesso: {ok_count} | Falhas: {len(results) - ok_count}")

        DASHBOARD_PATH = BASE_DIR / "results_dashboard.png"
        try:
            generate_infographic(payload, DASHBOARD_PATH)
        except Exception as e:
            print(f"Error creating result dashboard: {e}")


if __name__ == "__main__":
    main()

from typing import Any, Dict


def format_console_output(data: Dict[str, Any]):
    """
    Formata e imprime o JSON de análise clínica no terminal com cores e estrutura.
    """
    risk = data.get("risk_assessment", {})
    risk_level = risk.get("level", "N/A")
    risk_level_str = (
        risk_level.upper() if isinstance(risk_level, str) else str(risk_level)
    )
    report = data.get("clinical_report", {})

    # Formatação ANSI para terminais
    BOLD = "\033[1m"
    RESET = "\033[0m"
    RED = "\033[91m"
    YELLOW = "\033[33m"
    GREEN = "\033[92m"
    CYAN = "\033[96m"
    RISK_COLOR = {"ALTO": RED, "MÉDIO": YELLOW, "BAIXO": GREEN}

    # Lógica de cor baseada no risco
    color = RISK_COLOR.get(risk_level_str)

    print("\n" + "-" * 60)
    print(f"{BOLD}RELATÓRIO CLÍNICO{RESET}")
    print("-" * 60 + "\n")

    # ANÁLISE
    analysis_text = data.get("analysis", "Nenhuma análise gerada.")
    print(f"{BOLD}ANÁLISE:{RESET}\n{analysis_text}")

    # TEMAS E SIGNIFICANTES
    print(f"\n{BOLD}MAPA ESTRUTURAL:{RESET}")
    themes = data.get("themes", [])
    print(f"   {BOLD}Temas:{RESET} {', '.join(themes) if themes else 'N/A'}")
    signifiers = data.get("signifiers", [])
    print(
        f"   {BOLD}Significantes:{RESET} {', '.join(signifiers) if signifiers else 'N/A'}"
    )

    # HIPÓTESES
    print(f"\n{BOLD}HIPÓTESES:{RESET}")
    hypotheses = data.get("hypotheses", [])
    if hypotheses:
        for h in hypotheses:
            print(f" - {h}")
    else:
        print(" - Nenhuma hipótese gerada.")

    # AVALIAÇÃO DE RISCO
    print(f"\n{BOLD}AVALIAÇÃO DE RISCO:{RESET} {color}[{risk_level_str}]{RESET}")
    signals = risk.get("signals", [])
    if signals:
        print(f" Sinais: {', '.join(signals)}")

    # 5. LAUDO CLÍNICO (só exibe se for necessário)
    if report.get("required"):
        print(f"\n{BOLD}{RED}LAUDO NECESSÁRIO{RESET}")
        print(f"   {BOLD}Resumo:{RESET} {report.get('summary', 'Sem resumo.')}")
    else:
        print(f"\n{BOLD}{CYAN}LAUDO NÃO NECESSÁRIO{RESET}")

    # PERGUNTAS
    print(f"\n{BOLD}PERGUNTAS SUGERIDAS:{RESET}")
    questions = data.get("questions", [])
    if questions:
        for q in questions:
            print(f" - {q}")

    print("+" * 80 + "\n")


def run_interactive_mode(app, version: str):
    """
    Executa o loop principal do Chatbot.
    Args:
        app: O grafo compilado do LangGraph (StateGraph).
        version: A versão do prompt (v1 ou v2).
    """
    print("\n" + "-" * 50)
    print(f"   MODO INTERATIVO - Chatbot Psicanalítico [{version.upper()}]")
    print("   Digite 'sair' ou 'exit' para encerrar.")
    print("-" * 50)

    while True:
        try:
            user_input = input("\nDigite o relato do paciente: ")

            # Condição de saída
            if user_input.strip().lower() in ["sair", "exit"]:
                print("Encerrando sessão.")
                break

            # Ignora input vazio
            if not user_input.strip():
                continue

            print("Processando análise...")

            # Monta o estado inicial esperado pelo LangGraph
            initial = {
                "filename": "Terminal",
                "input_text": user_input,
                "prompt_version": version,
                "raw_response": None,
                "parsed_output": None,
                "errors": [],
            }

            # Invoca o grafo
            final = app.invoke(initial)

            # Exibe resultados
            if final.get("errors"):
                print(f"Erro ao processar: {final['errors']}")
            elif final.get("parsed_output"):
                format_console_output(final["parsed_output"].model_dump())
            else:
                print("Retorno vazio desconhecido (Erro silencioso).")

        except KeyboardInterrupt:
            print("\nInterrupção detectada (Ctrl+C). Saindo...")
            break
        except Exception as e:
            print(f"\nErro inesperado no loop: {e}")

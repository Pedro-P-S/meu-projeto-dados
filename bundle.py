import os
import subprocess

FILES = [
    ("SYSTEM_RULES", "_ai_context/00-rules.md"),
    ("DOC_MESTRE_CONTEXTO", "_ai_context/01-doc-mestre-contexto.md"),
    ("TAREFA_ATUAL", "_ai_context/02-task.md"),
]

def copy_to_clipboard(text: str):
    process = subprocess.Popen('clip', stdin=subprocess.PIPE, shell=True)
    process.communicate(input=text.encode('utf-16-le'))

def build_prompt():
    output = []
    for tag, filepath in FILES:
        if os.path.exists(filepath):
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read().strip()
                if not content and tag == "DOC_MESTRE_CONTEXTO":
                    content = "[PROJETO NOVO - DOCUMENTO MESTRE AINDA VAZIO. Inicialize conforme instruído na tarefa.]"
                output.append(f"<{tag}>\n{content}\n</{tag}>\n")
        else:
            print(f"[AVISO] Arquivo não encontrado: {filepath}")
            
    output.append(
        "Siga estritamente as diretrizes em <SYSTEM_RULES>, valide o estado atual em "
        "<DOC_MESTRE_CONTEXTO> e execute o que foi solicitado em <TAREFA_ATUAL>."
    )
    
    final_prompt = "\n".join(output)
    copy_to_clipboard(final_prompt)
    print(f"Prompt copiado para o Ctrl+V! ({len(final_prompt)} caracteres)")

if __name__ == "__main__":
    build_prompt()

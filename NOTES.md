# NOTAS

## Como entendi o problema

Na minha opinião, o problema podia ser abordado de duas formas:

1. Criação de uma pipeline que lida diretamente com o "paciente", cuja missão seria substituir um psicanalista humano.
2. Criação de um sistema que auxilie um psicanalista credenciado, servindo como uma espécie de assistente.

Eu pessoalmente optei por seguir a lógica da segunda opção, por achar que é a forma mais responsável de se usar a IA - visto a sensibilidade da área em que está sendo aplicada.

De qualquer forma, o problema era estruturar uma pipeline capaz de criar análises psicanalíticas de valor, seja para ajudar um paciente diretamente ou indiretamente. Para isso, o sistema deveria ser capaz de transformar os textos de input em objetos JSON contendo a análise clínica e seguindo certas regras de negócio.

Agora, os focos técnicos do teste me pareceram ser:

- Arquitetura e implementação das etapas da pipeline
- Engenharia de prompt
- Robustez e organização do código

## Estruturas e melhorias dos prompts

O primeiro prompt que escrevi foi o `v1`. A ideia dele é dar as instruções mínimas para que o agente tenha uma noção do contexto em que será atuando e o que se espera da sua resposta. Foquei também na organização lógica do prompt (usando MarkDown), separando-o em 4 seções: "tarefas", "instruções", "formato de saída" e "texto do paciente", pois julguei estas informações como sendo as mais relevantes para um prompt relativamente curto.

Após fazer alguns testes e ver o prompt em ação, percebi alguns problemas com os resultados:

1. **As análises clínicas geradas frequentemente patologizavam discursos totalmente comuns.** Por exemplo, se eu dava como input à IA o texto "Estou me sentindo normal. Não estou deprimido e minha vida está tranquila", ela frequentemente inseria em sua análise que o paciente estava em negação, mascarando sua dor ou reprimindo seus sentimentos. Isto gerava um tom até mesmo acusatório no output, provavelmente porque o Gemini estava assumindo como verdade à priori que havia algo de errado com o paciente.
2. **A linguagem era caricata e excessivamente clínica**. Parecia que o modelo estava se esforçando para encaixar o máximo possível de termos da psicanálise na resposta.
3. **Significantes sem sentido**. Alguns inputs (principalmente se curtos) faziam com que o modelo inserisse termos aleatórios na lista de significantes, como conectivos, pronomes, adjuntos, etc. Este era um problema um pouco mais difícil do que os demais, pois se não houvesse conteúdo o suficiente no input ele não deveria apenas inventar significantes para alcançar a quantidade mínima.
4. **Respostas vazias**. Com certa frequência, a API retornava uma resposta vazia. As causas podem ser muitas, mas possivelmente seria possível mitigar este efeito com uma melhoria no prompt.

Tendo tudo em vista tudo isso, fiz minhas melhorias na `v2` visando resolver estes problemas. As principais mudanças foram:

1. **Seção de Persona**: adicionei esta seção para contextualizar a tarefa do modelo.
2. **Modificação no formato de saída**: coloquei explicitamente o formato do JSON que deveria ser criado, reforçando desde cedo como deve ser gerado o output.
3. **Seção de Regras de Negócio**: inseri também as restrições do enunciado no prompt, juntamente com uma breve descrição de como ele deveria preencher cada campo do JSON.
4. **Seção de Diretrizes de Qualidade**: provavelmente a alteração mais importante, pois aborda diretamente os principais defeitos do prompt anterior. As instruções desta seção são ou negações dos comportamentos indesejados (patologização, linguagem caricata e significantes inúteis) ou clarificações dos comportamentos desejados.

Após testar mais o sistema com ambos os prompts, me questionei se seria possível obter um resultado satisfatório com uma prompt ultra-minimalista. Logo, criei a prompt `v0`, que se consiste em uma única frase. Em teoria, o a opção de output estruturado da API do Gemini já força a resposta a satisfazer o padrão definido pelo Pydantic, então o `prompt v0` também serviu de stress test para esta garantia.

Após mais alguns testes, pude ver que mesmo com uma prompt mínima, os resultados não eram nada ruins, e por vezes até mesmo superavam o `v1` por não seguir os mesmos vícios e vieses.

## Problemas que encontrei

- **Respostas inválidas**: obviamente nem toda requisição gerou uma resposta válida. Como citei anteriormente, algumas vezes a resposta era até mesmo uma string vazia. Para resolver isso, implementei um mecanismo de "Self-Healing" que corrige erros deste gênero. Para fazer isso, criei o nó de correção e o adicionei com arestas condicionais no `LangGraph`.
- **Loop Infinito de Correção**: ao tentar adicionar o nó de correção no grafo do LangGraph, acabei esbarrando em uma situação na qual o programa ficava preso em um loop entre os nós de validação e correção. O nó de validação encontrava um erro e desviava a pipeline para o nó de correção, que por sua vez não conseguia corrigir o erro e enviava de volta para a validação, e isto se repetia indefinidamente. Achei estranho à princípio, pois já havia implementado uma lógica que limitava o número de desvios para o nó de correção para 3. Contudo, a solução era simples: mover a linha que incrementava o contador de correções (que para no 3) para o topo da função de correção. Assim, mesmo se um erro fosse gerado no meio daquele nó, o contador já teria sido encrementado e o loop infinito não aconteceria.
- **Rate limit (erro 429)**: este não foi um problema de implementação como o anterior. O que acontece é que a API do Gemini impõe um limite de 20 requisições por dia às chaves gratuitas, então isto limitou e muito a quantide de testes que eu conseguia fazer por dia. Para circunvir esta limitação, criei projetos paralelos no dashboard do AIStudio (ferramenta onde controlamos as chaves de API) e adicionei novas chaves para alternar entre elas conforme se esgotavam.
- **Renderização de PDF**: eu nunca havia trabalhado com alguma biblioteca de criação de PDFs, então tive algumas dificuldades técnicas tentando criar os relatórios com a biblioteca `fpdf2`. No fim, acredito que o resultado ficou satisfatório.

## O que faria de diferente em produção

Eu vejo algumas limitações do projeto no que diz respeito à sua rigidez. Acredito que em produção seria interessante torná-lo mais versátil, permitindo que o usuário controle partes da pipeline ou até mesmo interfira diretamente nela, com um Human In The Loop (HITL). Também seria bom testar diferentes LLMs e fazer uma análise comparativa para selecionar a melhor delas (escolhi o Gemini por maior familiaridade e pela API elegante).
Por fim, acho que uma funcionalidade essencial seria a criação de "perfis" ou "sessões" que armazenem o avanço clínico de pacientes específios. Assim, as análises da IA poderiam ser baseadas não apenas em um relato isolado, mas sim em um banco maior de informações.

## Dificuldades

Na minha visão, as duas principais dificuldades que devem ser levadas em conta em um projeto deste são:

- **Considerações éticas**: o projeto envolve uma área bastante sensível até mesmo para parâmetros médicos. No contexto desta aplicação, a IA está sob a responsabilidade de interferir diretamente com a saúde mental de um indivíduo, e as implicações de delírios podem ser muito mais sérias do que o habitual. Sendo assim, para ser útil, este projeto teria que implementar o máximo de safeguards possível.
- **Barreiras de comunicação**: na psicologia (e fora dela também), as expressões faciais, o tom de voz e as emoções transmitidas de outras formas comunicam tanto quando as palavras em si. Sendo assim, o input em forma de texto impõe uma barreira de comunicação que torna muito difícil o entendimento total da subjetividade de um paciente até mesmo para um humano treinado, pois ele analisa também o __subtexto__. Na psicanálise lacaniana, por exemplo, o sarcarmo e a ironia desempenham um papel importante, mas são difíceis de detectar através do texto.

## Palavras finais

Espero que tenham gostado da minha solução! Este desafio com certeza me tirou da minha zona de conforto, mas achei ótimo aprender mais sobre o tema e colocar em prática algumas coisas que não tive oportunidade de colocar no passado.

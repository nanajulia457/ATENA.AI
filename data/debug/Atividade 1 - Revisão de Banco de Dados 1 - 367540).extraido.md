| <!-- image -->   | **Instituto Federal de Educação, Ciência e Tecnologia**   |
|------------------|-----------------------------------------------------------|
|                  | Câmpus Campinas  CMPBCD2 – Banco de Dados 2               |
| **Professor:**   | Everton Meyer da Silva (everton.silva@ifsp.edu.br)        |

### Objetivo

# Atividade 1

Atividade Prática de Banco de Dados Criação e Manipulação de Dados

Nesta atividade, você deverá criar e manipular um banco de dados que representa uma **Livraria** . Será necessário:

- Criar o banco de dados e as tabelas com chaves primárias, estrangeiras e demais restrições de integridade.
- Criar um novo usuário com permissões específicas para o banco.
- Inserir dados nas tabelas usando instruções INSERT INTO.
- Realizar consultas básicas (SELECT) para verificar o correto funcionamento do esquema de banco de dados.

O objetivo é praticar a criação de objetos de banco de dados, definição de chaves, restrições de integridade e manipulação de dados em SQL (MySQL)

### Etapas da atividade

##### Criação do banco de dados (1 ponto)

- Faça login no MySQL com o usuário root.
- Crie um banco de dados chamado **livraria** .
<!-- image -->

##### Criação de usuário e concessão de privilégios (1,5 pontos)

- Crie um novo usuário, por exemplo **userliv** com a senha **cmpbooks** .
- **Conceda privilégios ao novo usuário para que ele possa manipular o banco de dados livraria.**
<!-- image -->

##### Criação das tabelas (2 pontos)

- Faça login com o novo usuário que você criou.
- Crie as tabelas relacionadas à **livraria** . As tabelas devem ser as seguintes:

| <!-- image -->   | <!-- image -->   |
|------------------|------------------|
| <!-- image -->   | <!-- image -->   |
| <!-- image -->   |                  |

Crie todas as chaves primárias, estrangeiras e restrições de integridade (como **NOT NULL** , etc.) de acordo com sua modelagem.

##### Inserção de dados (2,5 pontos)

- Insira dados nas tabelas utilizando comandos **INSERT INTO** .
- Garanta que haja dados suficientes para testar as consultas que serão solicitadas posteriormente.

##### Definição de tipos de variáveis e integridade referencial (1 ponto)

- Defina corretamente os tipos de dados para cada coluna (VARCHAR, INT, DECIMAL, etc.).
- Crie corretamente as chaves primárias, estrangeiras e demais restrições de integridade (por exemplo NOT NULL, UNIQUE, CHECK, etc., quando aplicável).
- Certifique-se de que o banco de dados não permita gravação de dados inconsistentes.

##### Consultas SQL (2 pontos)

A seguir, alguns exemplos de consultas para testar o funcionamento do seu banco de dados. Você deve criar pelo menos as consultas solicitadas e garantir que retornem informações relevantes:

- a) **Listar todos os clientes cadastrados** , ordenados por nome.
- b) **Listar todas as vendas realizadas** , incluindo o nome do cliente e a data da venda.
- c) **Listar todos os livros** e a respectiva **editora** .
- d) **Contar quantas vendas cada cliente realizou** (exibir o nome do cliente e total de compras).
- e) **Listar todas as editoras** e o **número de livros** associados a cada uma.

#### Instruções de Entrega

- Responda às questões diretamente no seu script MySQL (todas as instruções CREATE DATABASE, CREATE TABLE, INSERT, SELECT, etc. em um arquivo único).
- **Exporte o script** como um arquivo **.sql** .
- O arquivo .sql deve conter todas as etapas mencionadas acima **sem erros de execução** .
- Nomeie o arquivo .sql como atv1.sql.
- Envie o arquivo pela plataforma Moodle no link em “Atividade 1 – Revisão de Banco de Dados 1”.

**Bons estudos e boa prática no desenvolvimento do seu banco de dados de livraria!**
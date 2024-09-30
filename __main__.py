# %% Importações
import json
import threading
import time
from datetime import datetime

import pywhatkit
import schedule
import tkinter as tk
from tkinter import messagebox, simpledialog, ttk

# %% Funções de gerenciamento de dados
def carregar_dados(nome_arquivo):
    """
    Carrega dados de um arquivo JSON.

    Args:
        nome_arquivo (str): Nome do arquivo JSON.

    Returns:
        dict: Dados carregados ou um dicionário vazio se o arquivo não existir.
    """
    try:
        with open(nome_arquivo, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def salvar_dados(dados, nome_arquivo):
    """
    Salva dados em um arquivo JSON.

    Args:
        dados (dict): Dados a serem salvos.
        nome_arquivo (str): Nome do arquivo JSON.
    """
    with open(nome_arquivo, 'w') as f:
        json.dump(dados, f)

# %% Funções principais
def adicionar_item():
    """Adiciona um novo item à lista de compras."""
    nome = entrada_nome.get()
    duracao = entrada_duracao.get()
    if nome and duracao:
        try:
            duracao = int(duracao)
            dados['itens'][nome] = {'duracao': duracao, 'ultima_compra': datetime.now().strftime("%Y-%m-%d")}
            salvar_dados(dados, 'dados_compras.json')
            atualizar_lista_itens()
            messagebox.showinfo("Sucesso", f"Item '{nome}' adicionado com sucesso!")
            entrada_nome.delete(0, tk.END)
            entrada_duracao.delete(0, tk.END)
        except ValueError:
            messagebox.showerror("Erro", "A duração deve ser um número inteiro.")
    else:
        messagebox.showerror("Erro", "Preencha todos os campos.")

def editar_item():
    """Edita um item existente na lista de compras."""
    selecionado = lista_itens.curselection()
    if selecionado:
        nome_antigo = lista_itens.get(selecionado[0])
        novo_nome = simpledialog.askstring("Editar Item", "Novo nome do item:", initialvalue=nome_antigo)
        if novo_nome:
            nova_duracao = simpledialog.askinteger("Editar Item", "Nova duração (em dias):", 
                                                   initialvalue=dados['itens'][nome_antigo]['duracao'])
            if nova_duracao is not None:
                dados['itens'][novo_nome] = dados['itens'].pop(nome_antigo)
                dados['itens'][novo_nome]['duracao'] = nova_duracao
                dados['itens'][novo_nome]['ultima_compra'] = datetime.now().strftime("%Y-%m-%d")
                salvar_dados(dados, 'dados_compras.json')
                atualizar_lista_itens()
                messagebox.showinfo("Sucesso", f"Item '{nome_antigo}' editado para '{novo_nome}'!")
    else:
        messagebox.showerror("Erro", "Selecione um item para editar.")

def apagar_item():
    """Remove um item da lista de compras."""
    selecionado = lista_itens.curselection()
    if selecionado:
        item = lista_itens.get(selecionado[0])
        if messagebox.askyesno("Confirmar", f"Deseja apagar '{item}'?"):
            del dados['itens'][item]
            salvar_dados(dados, 'dados_compras.json')
            atualizar_lista_itens()
            messagebox.showinfo("Sucesso", f"Item '{item}' apagado com sucesso!")
    else:
        messagebox.showerror("Erro", "Selecione um item para apagar.")

def registrar_compra():
    """Registra a compra de um item, atualizando a data da última compra."""
    selecionado = lista_itens.curselection()
    if selecionado:
        item = lista_itens.get(selecionado[0])
        dados['itens'][item]['ultima_compra'] = datetime.now().strftime("%Y-%m-%d")
        salvar_dados(dados, 'dados_compras.json')
        messagebox.showinfo("Sucesso", f"Compra de '{item}' registrada.")
    else:
        messagebox.showerror("Erro", "Selecione um item da lista.")

def gerar_lista_compras():
    """
    Gera uma lista de compras baseada na duração dos itens e última data de compra.

    Returns:
        list: Lista de itens que precisam ser comprados.
    """
    hoje = datetime.now()
    lista_compras = []
    for item, info in dados['itens'].items():
        ultima_compra = datetime.strptime(info['ultima_compra'], "%Y-%m-%d")
        dias_passados = (hoje - ultima_compra).days
        if dias_passados >= info['duracao'] * 0.8:
            lista_compras.append(item)
    return lista_compras

def enviar_whatsapp(mensagem):
    """
    Envia uma mensagem para o WhatsApp.

    Args:
        mensagem (str): Mensagem a ser enviada.
    """
    numero_telefone = dados.get('numero_telefone')
    if not numero_telefone:
        messagebox.showerror("Erro", "Número de telefone não configurado.")
        return
    try:
        pywhatkit.sendwhatmsg_instantly(numero_telefone, mensagem)
        print("Mensagem enviada com sucesso!")
    except Exception as e:
        print(f"Erro ao enviar a mensagem: {str(e)}")
    time.sleep(10)

def gerar_e_enviar_lista(automatico=False):
    """
    Gera a lista de compras e envia para o WhatsApp, se confirmado.

    Args:
        automatico (bool): Se True, envia automaticamente sem confirmação.
    """
    lista_compras = gerar_lista_compras()
    if lista_compras:
        mensagem = "Lista de Compras:\n" + "\n".join(f"- {item}" for item in lista_compras)
        if automatico:
            enviar_whatsapp(mensagem)
        else:
            if messagebox.askyesno("Lista de Compras", f"{mensagem}\n\nEnviar para o WhatsApp?"):
                enviar_whatsapp(mensagem)
    elif not automatico:
        messagebox.showinfo("Informação", "Não há itens para comprar no momento.")

def configurar_envio_automatico():
    """Configura a frequência de envio automático da lista de compras."""
    opcoes = ["Desativado", "Diário", "Semanal"]
    escolha = simpledialog.askstring("Configurar Envio Automático", 
                                     "Escolha a frequência (Desativado/Diário/Semanal):",
                                     initialvalue=dados.get('envio_automatico', 'Desativado'))
    if escolha and escolha.lower() in [op.lower() for op in opcoes]:
        dados['envio_automatico'] = escolha.lower()
        salvar_dados(dados, 'dados_compras.json')
        configurar_agendamento()
        messagebox.showinfo("Sucesso", f"Envio automático configurado para: {escolha}")
    else:
        messagebox.showerror("Erro", "Opção inválida.")

def configurar_agendamento():
    """Configura o agendamento de envio automático baseado na frequência escolhida."""
    schedule.clear()
    if dados.get('envio_automatico') == 'diário':
        schedule.every().day.at("09:00").do(gerar_e_enviar_lista, automatico=True)
    elif dados.get('envio_automatico') == 'semanal':
        schedule.every().monday.at("09:00").do(gerar_e_enviar_lista, automatico=True)

def executar_agendamento():
    """Executa o agendamento em um loop contínuo."""
    while True:
        schedule.run_pending()
        time.sleep(60)

def atualizar_lista_itens():
    """Atualiza a lista de itens na interface gráfica."""
    lista_itens.delete(0, tk.END)
    for item in dados['itens']:
        lista_itens.insert(tk.END, item)

def definir_numero_telefone():
    """Solicita e salva o número de telefone do usuário."""
    numero_atual = dados.get('numero_telefone', '')
    novo_numero = simpledialog.askstring("Número de Telefone", 
                                         "Digite seu número de telefone (com código do país):",
                                         initialvalue=numero_atual)
    if novo_numero:
        dados['numero_telefone'] = novo_numero
        salvar_dados(dados, 'dados_compras.json')
        messagebox.showinfo("Sucesso", "Número de telefone atualizado com sucesso!")
    elif not numero_atual:
        messagebox.showwarning("Aviso", "É necessário fornecer um número de telefone para enviar mensagens.")

# %% Configuração da interface gráfica
root = tk.Tk()
root.title("Gerenciador de Lista de Compras")

frame = ttk.Frame(root, padding="10")
frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

ttk.Label(frame, text="Nome do Item:").grid(column=0, row=0, sticky=tk.W)
entrada_nome = ttk.Entry(frame, width=20)
entrada_nome.grid(column=1, row=0, sticky=(tk.W, tk.E))

ttk.Label(frame, text="Duração (dias):").grid(column=0, row=1, sticky=tk.W)
entrada_duracao = ttk.Entry(frame, width=20)
entrada_duracao.grid(column=1, row=1, sticky=(tk.W, tk.E))

ttk.Button(frame, text="Adicionar Item", command=adicionar_item).grid(column=0, row=2, columnspan=2, sticky=tk.W)

frame_lista = ttk.Frame(frame)
frame_lista.grid(column=0, row=3, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S))

lista_itens = tk.Listbox(frame_lista, height=10, width=30)
lista_itens.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

barra_rolagem = ttk.Scrollbar(frame_lista, orient=tk.VERTICAL, command=lista_itens.yview)
barra_rolagem.pack(side=tk.RIGHT, fill=tk.Y)

lista_itens.config(yscrollcommand=barra_rolagem.set)

ttk.Button(frame, text="Registrar Compra", command=registrar_compra).grid(column=0, row=4, sticky=tk.W)
ttk.Button(frame, text="Gerar e Enviar Lista", command=gerar_e_enviar_lista).grid(column=1, row=4, sticky=tk.E)
ttk.Button(frame, text="Apagar Item", command=apagar_item).grid(column=0, row=5, sticky=tk.W)
ttk.Button(frame, text="Editar Item", command=editar_item).grid(column=1, row=5, sticky=tk.E)
ttk.Button(frame, text="Configurar Envio Automático", command=configurar_envio_automatico).grid(column=0, row=6, columnspan=2)
ttk.Button(frame, text="Configurar Número de Telefone", command=definir_numero_telefone).grid(column=0, row=7, columnspan=2)

root.columnconfigure(0, weight=1)
root.rowconfigure(0, weight=1)
frame.columnconfigure(1, weight=1)
frame.rowconfigure(3, weight=1)

# %% Inicialização
dados = carregar_dados('dados_compras.json')
if 'itens' not in dados:
    dados['itens'] = {}
atualizar_lista_itens()

if not dados.get('numero_telefone'):
    definir_numero_telefone()

thread_agendamento = threading.Thread(target=executar_agendamento, daemon=True)
thread_agendamento.start()

configurar_agendamento()

root.mainloop()

#!/usr/bin/env python3
"""
💼 MEI Assistente Bot - Bot para MEI e Autônomos
Organiza cobranças, contas a receber e a pagar via Telegram
"""

import logging
import os
import json
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters
)

# =============================================
# CONFIGURAÇÕES — EDITE AQUI
# =============================================
BOT_TOKEN = "8832721667:AAFqpTJpk7OiEgA3LJ1E_fUlz7zRKs4nbPo"           # Token do BotFather
HOTMART_WEBHOOK_SECRET = "SEU_SECRET"  # Para validar pagamentos
ADMIN_ID = 982810635                   # Seu ID do Telegram (use @userinfobot)
PRECO_ASSINATURA = "R$14,90"

# =============================================
# BANCO DE DADOS SIMPLES (arquivo JSON)
# =============================================
DB_FILE = "dados.json"

def carregar_dados():
    if not os.path.exists(DB_FILE):
        return {"assinantes": {}, "lancamentos": {}}
    with open(DB_FILE, "r") as f:
        return json.load(f)

def salvar_dados(dados):
    with open(DB_FILE, "w") as f:
        json.dump(dados, f, ensure_ascii=False, indent=2)

def usuario_ativo(user_id: int) -> bool:
    dados = carregar_dados()
    assinante = dados["assinantes"].get(str(user_id))
    if not assinante:
        return False
    validade = datetime.fromisoformat(assinante["validade"])
    return validade > datetime.now()

def ativar_usuario(user_id: int, nome: str, dias: int = 30):
    dados = carregar_dados()
    validade = datetime.now() + timedelta(days=dias)
    dados["assinantes"][str(user_id)] = {
        "nome": nome,
        "validade": validade.isoformat(),
        "ativo_desde": datetime.now().isoformat()
    }
    salvar_dados(dados)

def get_lancamentos(user_id: int) -> dict:
    dados = carregar_dados()
    uid = str(user_id)
    if uid not in dados["lancamentos"]:
        dados["lancamentos"][uid] = {"receber": [], "pagar": []}
        salvar_dados(dados)
    return dados["lancamentos"][uid]

def salvar_lancamentos(user_id: int, lancamentos: dict):
    dados = carregar_dados()
    dados["lancamentos"][str(user_id)] = lancamentos
    salvar_dados(dados)

# =============================================
# TECLADOS
# =============================================
def teclado_principal():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💰 Registrar Recebimento", callback_data="registrar_receber")],
        [InlineKeyboardButton("📋 Registrar Conta a Pagar", callback_data="registrar_pagar")],
        [InlineKeyboardButton("📊 Ver Resumo do Mês", callback_data="resumo")],
        [InlineKeyboardButton("✅ Ver Contas a Receber", callback_data="listar_receber")],
        [InlineKeyboardButton("❗ Ver Contas a Pagar", callback_data="listar_pagar")],
        [InlineKeyboardButton("🗑️ Limpar Tudo", callback_data="limpar_confirmar")],
    ])

def teclado_assinar():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Assinar por R$14,90/mês", url="https://pay.kiwify.com.br/fSG4NpF")],
        [InlineKeyboardButton("🎁 Testar 3 dias grátis", callback_data="teste_gratis")],
    ])

# =============================================
# COMANDOS
# =============================================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    nome = user.first_name

    if usuario_ativo(user.id):
        await update.message.reply_text(
            f"👋 Olá, {nome}! Seu bot MEI está ativo.\n\n"
            "O que você quer fazer hoje?",
            reply_markup=teclado_principal()
        )
        return

    await update.message.reply_text(
        f"👋 Olá, {nome}! Eu sou o *MEI Assistente*.\n\n"
        "📌 Eu ajudo você a:\n"
        "• Registrar o que vai receber\n"
        "• Anotar contas a pagar\n"
        "• Ver resumo do mês na hora\n"
        "• Não perder prazo de nenhum boleto\n\n"
        f"💳 Tudo isso por apenas *{PRECO_ASSINATURA}/mês*.\n\n"
        "👇 Escolha uma opção:",
        parse_mode="Markdown",
        reply_markup=teclado_assinar()
    )

async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not usuario_ativo(update.effective_user.id):
        await update.message.reply_text(
            "⛔ Você não tem assinatura ativa.\n\nClique abaixo para assinar:",
            reply_markup=teclado_assinar()
        )
        return
    await update.message.reply_text(
        "📋 *Menu Principal*\n\nO que você quer fazer?",
        parse_mode="Markdown",
        reply_markup=teclado_principal()
    )

async def ativar_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando secreto para admin ativar usuários manualmente"""
    if update.effective_user.id != ADMIN_ID:
        return
    args = context.args
    if len(args) < 2:
        await update.message.reply_text("Uso: /ativar <user_id> <nome>")
        return
    uid = int(args[0])
    nome = " ".join(args[1:])
    ativar_usuario(uid, nome, dias=30)
    await update.message.reply_text(f"✅ Usuário {nome} ({uid}) ativado por 30 dias!")
    try:
        await context.bot.send_message(
            uid,
            "🎉 Sua assinatura foi ativada!\n\nUse /menu para começar.",
        )
    except:
        pass

async def teste_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ativa teste grátis de 3 dias"""
    if update.effective_user.id != ADMIN_ID:
        return
    args = context.args
    if not args:
        return
    uid = int(args[0])
    ativar_usuario(uid, "Usuário Teste", dias=3)
    await update.message.reply_text(f"✅ Teste ativado para {uid}")

# =============================================
# CALLBACKS DOS BOTÕES
# =============================================
async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = query.data

    if data == "teste_gratis":
        if usuario_ativo(user_id):
            await query.edit_message_text("Você já tem uma assinatura ativa! Use /menu")
            return
        ativar_usuario(query.from_user.first_name, query.from_user.first_name, dias=3)
        ativar_usuario(user_id, query.from_user.first_name, dias=3)
        await query.edit_message_text(
            "🎁 *Teste grátis ativado por 3 dias!*\n\n"
            "Explore tudo e veja como é fácil organizar suas finanças.\n\n"
            "Ao final, assine para continuar por apenas R$14,90/mês.",
            parse_mode="Markdown",
            reply_markup=teclado_principal()
        )
        return

    if not usuario_ativo(user_id):
        await query.edit_message_text(
            "⛔ Assinatura necessária para usar este recurso.",
            reply_markup=teclado_assinar()
        )
        return

    if data == "registrar_receber":
        context.user_data["aguardando"] = "receber"
        await query.edit_message_text(
            "💰 *Registrar Recebimento*\n\n"
            "Me mande uma mensagem no formato:\n\n"
            "`Nome do cliente | Valor | Data (dd/mm)`\n\n"
            "Exemplo:\n"
            "`João Silva | 350,00 | 25/06`",
            parse_mode="Markdown"
        )

    elif data == "registrar_pagar":
        context.user_data["aguardando"] = "pagar"
        await query.edit_message_text(
            "📋 *Registrar Conta a Pagar*\n\n"
            "Me mande uma mensagem no formato:\n\n"
            "`Descrição | Valor | Vencimento (dd/mm)`\n\n"
            "Exemplo:\n"
            "`Aluguel sala | 800,00 | 10/07`",
            parse_mode="Markdown"
        )

    elif data == "resumo":
        await mostrar_resumo(query, user_id)

    elif data == "listar_receber":
        await listar_itens(query, user_id, "receber")

    elif data == "listar_pagar":
        await listar_itens(query, user_id, "pagar")

    elif data == "limpar_confirmar":
        await query.edit_message_text(
            "⚠️ Tem certeza que quer apagar TODOS os lançamentos deste mês?",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🗑️ Sim, apagar tudo", callback_data="limpar_confirmar_sim")],
                [InlineKeyboardButton("❌ Cancelar", callback_data="menu_voltar")],
            ])
        )

    elif data == "limpar_confirmar_sim":
        salvar_lancamentos(user_id, {"receber": [], "pagar": []})
        await query.edit_message_text(
            "✅ Tudo limpo! Novo mês zerado.",
            reply_markup=teclado_principal()
        )

    elif data == "menu_voltar":
        await query.edit_message_text(
            "📋 *Menu Principal*", parse_mode="Markdown",
            reply_markup=teclado_principal()
        )

async def mostrar_resumo(query, user_id: int):
    lancamentos = get_lancamentos(user_id)
    receber = lancamentos.get("receber", [])
    pagar = lancamentos.get("pagar", [])

    total_receber = sum(item["valor"] for item in receber)
    total_pagar = sum(item["valor"] for item in pagar)
    saldo = total_receber - total_pagar

    emoji_saldo = "🟢" if saldo >= 0 else "🔴"

    texto = (
        f"📊 *Resumo do Mês*\n"
        f"{'─'*25}\n\n"
        f"💰 A Receber: *R$ {total_receber:,.2f}*\n"
        f"   ({len(receber)} lançamento(s))\n\n"
        f"❗ A Pagar: *R$ {total_pagar:,.2f}*\n"
        f"   ({len(pagar)} lançamento(s))\n\n"
        f"{'─'*25}\n"
        f"{emoji_saldo} Saldo Previsto: *R$ {saldo:,.2f}*"
    )

    await query.edit_message_text(
        texto, parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("⬅️ Voltar ao Menu", callback_data="menu_voltar")]
        ])
    )

async def listar_itens(query, user_id: int, tipo: str):
    lancamentos = get_lancamentos(user_id)
    itens = lancamentos.get(tipo, [])

    if not itens:
        emoji = "💰" if tipo == "receber" else "❗"
        await query.edit_message_text(
            f"{emoji} Nenhum lançamento registrado ainda.\n\nUse o menu para adicionar.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅️ Voltar", callback_data="menu_voltar")]
            ])
        )
        return

    emoji = "💰" if tipo == "receber" else "❗"
    titulo = "Contas a Receber" if tipo == "receber" else "Contas a Pagar"
    total = sum(i["valor"] for i in itens)

    linhas = [f"{emoji} *{titulo}*\n{'─'*25}"]
    for i, item in enumerate(itens, 1):
        linhas.append(f"{i}. {item['descricao']}\n   R$ {item['valor']:,.2f} — {item['data']}")

    linhas.append(f"{'─'*25}\n💡 Total: *R$ {total:,.2f}*")

    await query.edit_message_text(
        "\n".join(linhas), parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("⬅️ Voltar ao Menu", callback_data="menu_voltar")]
        ])
    )

# =============================================
# MENSAGENS DE TEXTO (LANÇAMENTOS)
# =============================================
async def processar_mensagem(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if not usuario_ativo(user_id):
        await update.message.reply_text(
            "⛔ Você precisa de uma assinatura ativa.",
            reply_markup=teclado_assinar()
        )
        return

    aguardando = context.user_data.get("aguardando")

    if not aguardando:
        await update.message.reply_text(
            "Use o menu para navegar 👇",
            reply_markup=teclado_principal()
        )
        return

    texto = update.message.text.strip()
    partes = [p.strip() for p in texto.split("|")]

    if len(partes) != 3:
        await update.message.reply_text(
            "⚠️ Formato inválido! Use:\n\n`Descrição | Valor | Data`\n\nExemplo:\n`João Silva | 350,00 | 25/06`",
            parse_mode="Markdown"
        )
        return

    descricao, valor_str, data = partes

    try:
        valor = float(valor_str.replace(".", "").replace(",", "."))
    except ValueError:
        await update.message.reply_text("⚠️ Valor inválido. Use o formato: `350,00`", parse_mode="Markdown")
        return

    lancamentos = get_lancamentos(user_id)
    lancamentos[aguardando].append({
        "descricao": descricao,
        "valor": valor,
        "data": data,
        "criado_em": datetime.now().isoformat()
    })
    salvar_lancamentos(user_id, lancamentos)

    tipo_texto = "recebimento" if aguardando == "receber" else "conta a pagar"
    emoji = "✅" if aguardando == "receber" else "📌"

    context.user_data["aguardando"] = None

    await update.message.reply_text(
        f"{emoji} *{tipo_texto.capitalize()} registrado!*\n\n"
        f"📝 {descricao}\n"
        f"💵 R$ {valor:,.2f}\n"
        f"📅 {data}\n\n"
        "O que mais você quer fazer?",
        parse_mode="Markdown",
        reply_markup=teclado_principal()
    )

# =============================================
# MAIN
# =============================================
def main():
    logging.basicConfig(level=logging.INFO)

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("menu", menu))
    app.add_handler(CommandHandler("ativar", ativar_admin))
    app.add_handler(CommandHandler("teste", teste_admin))
    app.add_handler(CallbackQueryHandler(callback_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, processar_mensagem))

    print("🤖 MEI Assistente Bot rodando...")
    app.run_polling()

if __name__ == "__main__":
    main()

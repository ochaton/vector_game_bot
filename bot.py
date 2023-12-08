from configparser import ConfigParser
import logging
from embeddings import OpenaiClient
import telebot
import re
from telebot.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

parser = ConfigParser()
parser.read("configs.ini")

token = parser["DEFAULTS"].get("TOKEN")
api_key = parser["DEFAULTS"].get("API_KEY")


bot = telebot.TeleBot(token)
client = OpenaiClient(api_key)

games = {}

logging.basicConfig(filename="logs.log", format="%(asctime)s %(message)s", filemode="w")
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)


def contains_only_english_letters(word):
    return bool(re.match("^[a-zA-Z]+$", word))


def get_parameter(text):
    try:
        return text.split()[1] if 3 > len(text.split()) > 1 else False
    except:
        return False


@bot.message_handler(commands=["start", "help"])
def start(message: Message):
    try:
        param = get_parameter(message.text)
        if not param:
            bot.send_message(
                message.chat.id,
                "👋 Привет! Я - бот, с помощью которого можно загадывать слова, чтобы твои друзья их отгадывали. Я буду давать им подсказки и указывать, насколько они близки к правильному слову. Чтобы загадать слово, напиши в группе /play. (Играть надо на английском языке)",
            )
        else:
            if message.chat.type == "private":
                if param.startswith("pick"):
                    group_id = param[4:]
                    if games.get(str(group_id)) is not None:
                        bot.send_message(message.chat.id, "❌ Игра уже идет!")
                    else:
                        answer_message = bot.send_message(
                            message.chat.id,
                            "Отправь мне слово, которое хочешь загадать! 😨",
                        )
                        bot.register_next_step_handler(
                            answer_message, start_word_picking, int(group_id)
                        )
            else:
                bot.send_message(
                    message.chat.id,
                    "❌ Команду с параметром можно использовать только в личных сообщениях!",
                )
    except Exception as e:
        bot.send_message(
            message.chat.id,
            f"⛔ Возникла ошибка, пожалуйста, сообщите об этом @FoxFil\n\nОшибка:\n\n`{e}`",
            parse_mode="Markdown",
        )


@bot.message_handler(commands=["play"])
def play(message: Message):
    try:
        if not message.chat.type == "private":
            if games.get(str(message.chat.id)) is None:
                bot.send_message(
                    message.chat.id,
                    "Чтобы загадать слово, нажми на кнопку ниже! 😁",
                    reply_markup=InlineKeyboardMarkup(
                        [
                            [
                                InlineKeyboardButton(
                                    text="Загадать!",
                                    url=f"https://t.me/VectorGame_bot?start=pick{message.chat.id}",
                                )
                            ],
                        ]
                    ),
                )
            else:
                bot.send_message(
                    message.chat.id,
                    f"❌ Игра уже идет!",
                    parse_mode="Markdown",
                )
        else:
            bot.send_message(
                message.chat.id,
                "❌ Эту команду можно использовать только в групповом чате!",
            )
    except Exception as e:
        bot.send_message(
            message.chat.id,
            f"⛔ Возникла ошибка, пожалуйста, сообщите об этом @FoxFil\n\nОшибка:\n\n`{e}`",
            parse_mode="Markdown",
        )


def start_word_picking(message: Message, group_id: int):
    try:
        if games.get(str(group_id)) is not None:
            bot.send_message(message.chat.id, "❌ Игра уже идет!")
        else:
            answer = message.text.strip().lower()
            if not len(answer.split()) > 1:
                if contains_only_english_letters(answer):
                    answer_embedding = client.get_embedding(answer)
                    if client.exist(answer_embedding):
                        logging.info(f"{answer} | {group_id}")

                        games[str(group_id)] = [
                            answer,
                            {},
                            "",
                            {},
                        ]

                        image_generation = bot.send_message(
                            message.chat.id,
                            "Картинка генерируется 😎",
                        )
                        url = client.generate_image(answer)
                        if url[0] == 200:
                            bot.send_photo(
                                group_id,
                                url[1],
                                f"Пользователь *{message.from_user.full_name}* загадал слово! Пишите свои ответы в формате `/guess ответ` в этом чате!",
                                parse_mode="Markdown",
                            )
                            bot.delete_message(
                                message.chat.id, image_generation.message_id
                            )
                            games[str(group_id)] = [
                                answer,
                                {},
                                url[1],
                                {},
                            ]
                            bot.send_message(
                                message.chat.id,
                                "Ваше слово успешно загадано! ✅ Перейдите обратно в группу.",
                            )

                            logging.info(f"game in {group_id} started")
                        else:
                            games.pop(str(group_id))
                            bot.delete_message(
                                message.chat.id, image_generation.message_id
                            )
                            bot.send_message(
                                message.chat.id,
                                f"❌ Ошибка генерации: `{url[1]}`",
                                parse_mode="Markdown",
                            )
                            bot.send_message(
                                group_id,
                                f"❌ Ошибка генерации. Начните игру заново: `{url[1]}`",
                                parse_mode="Markdown",
                            )
                    else:
                        bot.send_message(
                            message.chat.id,
                            "❌ Такого слова не существует!",
                            reply_markup=InlineKeyboardMarkup(
                                [
                                    [
                                        InlineKeyboardButton(
                                            text="Загадать заново!",
                                            url=f"https://t.me/VectorGame_bot?start=pick{group_id}",
                                        )
                                    ],
                                ]
                            ),
                        )
                else:
                    bot.send_message(
                        message.chat.id,
                        "❌ Слово должно быть английским и состоять только из букв!",
                        reply_markup=InlineKeyboardMarkup(
                            [
                                [
                                    InlineKeyboardButton(
                                        text="Загадать заново!",
                                        url=f"https://t.me/VectorGame_bot?start=pick{group_id}",
                                    )
                                ],
                            ]
                        ),
                    )
            else:
                bot.send_message(
                    message.chat.id,
                    "❌ Пришли мне слово, а не предложение!",
                    reply_markup=InlineKeyboardMarkup(
                        [
                            [
                                InlineKeyboardButton(
                                    text="Загадать заново!",
                                    url=f"https://t.me/VectorGame_bot?start=pick{group_id}",
                                )
                            ],
                        ]
                    ),
                )
    except Exception as e:
        bot.send_message(
            message.chat.id,
            f"⛔ Возникла ошибка, пожалуйста, сообщите об этом @FoxFil\n\nОшибка:\n\n`{e}`",
            parse_mode="Markdown",
        )


@bot.message_handler(commands=["guess"])
def guess(message: Message):
    try:
        group_id = message.chat.id

        if games.get(str(group_id)) is None:
            bot.send_message(message.chat.id, "❌ Сейчас не идет никакая игра!")
        else:
            if not message.chat.type == "private":
                param = get_parameter(message.text)
                if param:
                    if contains_only_english_letters(param):
                        given_try = param.lower().strip()
                        correct_answer = games[str(group_id)][0].lower().strip()
                        if correct_answer == given_try:
                            if games.get(str(group_id)) is not None:
                                games[str(group_id)][3][
                                    message.from_user.first_name
                                ] = games[str(group_id)][3].get(
                                    message.from_user.first_name, []
                                ) + [
                                    100
                                ]
                                top_final("10", message.chat.id)
                                scoreboard_final(message.chat.id)
                                if (
                                    len(
                                        games[str(group_id)][3][
                                            message.from_user.first_name
                                        ]
                                    )
                                    == 1
                                ):
                                    bot.send_message(
                                        group_id,
                                        f"🎉 *{message.from_user.full_name}* молодец! Ты отгадал слово *{correct_answer}* с первой попытки! Вот это мастерство! 🤯",
                                        parse_mode="Markdown",
                                    )
                                else:
                                    bot.send_message(
                                        group_id,
                                        f"🎉 *{message.from_user.full_name}* отгадал слово *{correct_answer}*! Игра заканчивается.",
                                        parse_mode="Markdown",
                                    )
                                games.pop(str(group_id))
                            else:
                                bot.send_message(
                                    message.chat.id, "❌ Сейчас не идет никакая игра!"
                                )
                        else:
                            correct_embedding = client.get_embedding(correct_answer)
                            given_try_embedding = client.get_embedding(given_try)

                            if client.exist(given_try_embedding):
                                div = client.cosine_similarity(
                                    correct_embedding, given_try_embedding
                                )
                                bot.send_message(
                                    group_id,
                                    f"Ответ *{message.from_user.full_name}* близок к правильному на *{round(div * 100, 2)}%*",
                                    parse_mode="Markdown",
                                )
                                if games.get(str(group_id)) is not None:
                                    games[str(group_id)][1][
                                        given_try
                                    ] = f"{round(div * 100, 2)}%"

                                    games[str(group_id)][3][
                                        message.from_user.first_name
                                    ] = games[str(group_id)][3].get(
                                        message.from_user.first_name, []
                                    ) + [
                                        round(div * 100, 2)
                                    ]

                            else:
                                bot.send_message(
                                    message.chat.id,
                                    f"❌ *{message.from_user.full_name}*, такого слова не существует!",
                                    parse_mode="Markdown",
                                )

                    else:
                        bot.send_message(
                            message.chat.id,
                            f"❌ *{message.from_user.full_name}*, отгадка должна быть на английском языке и состоять только из букв!",
                            parse_mode="Markdown",
                        )
                else:
                    bot.send_message(
                        message.chat.id,
                        f"❌ *{message.from_user.full_name}*, отгадка должна быть одним словом!",
                        parse_mode="Markdown",
                    )
            else:
                bot.send_message(
                    message.chat.id,
                    "❌ Эту команду можно использовать только в групповом чате!",
                )
    except Exception as e:
        bot.send_message(
            message.chat.id,
            f"⛔ Возникла ошибка, пожалуйста, сообщите об этом @FoxFil\n\nОшибка:\n\n`{e}`",
            parse_mode="Markdown",
        )


@bot.message_handler(commands=["top"])
def top(message: Message):
    try:
        if games.get(str(message.chat.id)) != None:
            param = get_parameter(message.text)
            if not param:
                param = "5"
            if param.isdigit():
                count = int(param)
                if 1 <= count <= 100:
                    prep_val = games[str(message.chat.id)][1]
                    if len(prep_val.keys()) != 0:
                        sorted_words = list(
                            sorted(
                                list(prep_val.items()),
                                key=lambda x: float(x[1][:-1]),
                                reverse=True,
                            )
                        )

                        count = (
                            len(sorted_words) if len(sorted_words) < count else count
                        )

                        top = sorted_words[:count]

                        output = ""
                        for i, (word, percentage) in enumerate(top, start=1):
                            output += f"{i}) *{word}*: {percentage}\n"

                        bot.send_message(message.chat.id, output, parse_mode="Markdown")
                        bot.send_photo(message.chat.id, games[str(message.chat.id)][2])
                    else:
                        bot.send_message(
                            message.chat.id,
                            f"❌ *{message.from_user.full_name}*, никаких отгадок еще нет!",
                            parse_mode="Markdown",
                        )

                else:
                    bot.send_message(
                        message.chat.id,
                        f"❌ *{message.from_user.full_name}*, укажите количество слов для вывода от 1 до 100.",
                        parse_mode="Markdown",
                    )
            else:
                bot.send_message(
                    message.chat.id,
                    f"❌ *{message.from_user.full_name}*, параметр должен быть числом (от 1 до 100)!",
                    parse_mode="Markdown",
                )
        else:
            bot.send_message(
                message.chat.id,
                f"❌ *{message.from_user.full_name}*, игра в данный момент не идет",
                parse_mode="Markdown",
            )
    except Exception as e:
        bot.send_message(
            message.chat.id,
            f"⛔️ Возникла ошибка, пожалуйста, сообщите об этом @FoxFil\n\nОшибка:\n\n`{e}`",
            parse_mode="Markdown",
        )


def top_final(amount: str, id: int):
    prep_val = games[str(id)][1]

    if len(prep_val.keys()) != 0:
        count = int(amount)

        sorted_words = list(
            sorted(list(prep_val.items()), key=lambda x: float(x[1][:-1]), reverse=True)
        )

        count = len(sorted_words) if len(sorted_words) < count else count

        top = sorted_words[:count]

        output = "Статистика по словам:\n\n"
        for i, (word, percentage) in enumerate(top, start=1):
            output += f"{i}) *{word}*: {percentage}\n"

        bot.send_message(id, output, parse_mode="Markdown")


def scoreboard_final(id: int):
    players = games[str(id)][3]

    output_list = []
    for elem in players.items():
        output_list.append([elem[0], len(elem[1]), sum(elem[1]) / len(elem[1])])

    output_list.sort(key=lambda x: x[2], reverse=True)

    result = "Статистика по пользователям (количество угадываний, средний показатель совпадения):\n\n"

    max_nick = max(players.keys(), key=lambda x: (len(x) + len(str(players[x][0]))))

    max_len = len(max_nick) + len(str(len(players[max_nick])))

    for elem in output_list:
        result += f"`{elem[0]}: {' ' * (max_len - len(elem[0]) - len(str(elem[1])))}{elem[1]} | {round(elem[2])}%`\n"

    bot.send_message(id, result, parse_mode="Markdown")


bot.infinity_polling()
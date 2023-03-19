from datetime import datetime
from aiogram import types, Router, F
from aiogram.fsm.context import FSMContext

from tgbot.keyboards.main_kb import main_kb_builder
from tgbot.keyboards.notes_kb import notes_ikb
from tgbot.keyboards.read_note_ikb import read_ikb
from tgbot.misc.funcs import validate_date
from tgbot.models.db_commands import save_visit
from tgbot.models.db_visit_commands import retrieve_note_info, get_info_about_date
from tgbot.states.note_states import NoteState
from tgbot.models.client import Visit

router = Router()


@router.callback_query(F.data == 'notes')
async def notes(callback_query: types.CallbackQuery, state: FSMContext):
    await callback_query.answer()
    data = await state.get_data()
    client_notes = await retrieve_note_info(data['fio'])
    if client_notes == 'Нет записей о клиенте':
        await callback_query.message.answer('Нет записей о клиенте',
                                            reply_markup=notes_ikb.as_markup())

    else:
        client_notes = list(map(lambda client: f'{"<code>"}{client}{"</code>"}', client_notes))
        one_note = '\n'.join(client_notes)
        await callback_query.message.answer(f'Записи клиента 📖\n\n'
                                            f'{one_note}\n\n',
                                            reply_markup=notes_ikb.as_markup())


# Добавление записи
@router.callback_query(F.data == 'note_add')
async def add_note(callback_query: types.CallbackQuery | types.Message, state: FSMContext):
    await callback_query.answer()
    await state.set_state(NoteState.note_date)
    await callback_query.message.answer('Введите, пожалуйста, дату приема клиента в формате 01.01.1111 ⏱')


@router.callback_query(F.data == 'note_read')
async def open_note(callback_query: types.CallbackQuery, state: FSMContext):
    await callback_query.answer()
    await state.set_state(NoteState.note_open)
    await callback_query.message.answer('Введите дату приема клиента')


@router.message(NoteState.note_open)
async def note_read(message: types.Message, state: FSMContext):
    await state.update_data(date=datetime.strptime(message.text, '%Y-%m-%d'))
    data = await state.get_data()
    output_data = await get_info_about_date(data)
    await message.answer(output_data, reply_markup=read_ikb.as_markup())


@router.callback_query(F.data == 'more_note')
async def note_one_more(callback_query: types.CallbackQuery, state: FSMContext):
    await open_note(callback_query, state)


@router.callback_query(F.data == 'cancel_note')
async def cancel_note(callback_query: types.CallbackQuery, state: FSMContext):
    await callback_query.answer()
    await state.clear()
    await callback_query.message.answer('До скорых встреч!',
                                        reply_markup=main_kb_builder.as_markup(resize_keyboard=True))


@router.message(NoteState.note_date)
async def add_note_date(message: types.Message, state: FSMContext):
    if validate_date(message.text):
        await state.update_data(date=datetime.strptime(message.text, '%d.%m.%Y'))
        await state.set_state(NoteState.note_procedures)
        await message.answer('Спасибо! Теперь сообщите какие процедуры проводили с клиентом? 💉')
    else:
        await message.answer('Вы ввели неправильный формат даты. Попробуйте еще раз.')


@router.message(NoteState.note_procedures)
async def add_note_procedures(message: types.Message, state: FSMContext):
    await state.update_data(procedures=message.text)
    await state.set_state(NoteState.note_recommendations)
    await message.answer('Имеются ли какие-либо рекомендации?')


@router.message(NoteState.note_recommendations)
async def add_note_recommendations(message: types.Message, state: FSMContext):
    await state.update_data(recommendations=message.text)
    data = await state.get_data()
    await save_visit(data)
    await message.answer('Информация о записи была успешно сохранена! ✅')

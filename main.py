from tkinter import filedialog
from fastapi import UploadFile, File, FastAPI
import io
import pandas as pd
import os
import json
import plotly.express as px
from fastapi.responses import JSONResponse
from starlette.responses import FileResponse
from starlette.staticfiles import StaticFiles
from fastapi import FastAPI, File, UploadFile, Form
from io import BytesIO



app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")


def process_file(file_content, file_type):
    columnnames = ['Дата', 'Цена нефти, $']
    if "csv" in file_type:
        df = pd.read_csv(io.BytesIO(file_content), delimiter=';|:', engine='python')
        # Добавьте здесь обработку для CSV-файлов
    elif "excel" in file_type:
        df = pd.read_excel(io.BytesIO(file_content), names=columnnames)
        # Добавьте здесь обработку для Excel-файлов
    else:
        # Добавьте обработку для других типов файлов или выведите ошибку, если тип файла не поддерживается
        return {"error": "Unsupported file type"}

    df.dropna(inplace=True)
    month_dict = {
        'январь': 1, 'февраль': 2, 'март': 3, 'апрель': 4, 'май': 5, 'июнь': 6,
        'июль': 7, 'август': 8, 'сентябрь': 9, 'октябрь': 10, 'ноябрь': 11, 'декабрь': 12
    }

    # Преобразование названия месяца в числовой формат
    df['Дата'] = df['Дата'].str.split(', ').apply(lambda x: f"{x[0]}-{month_dict.get(x[1], x[1])}")

    # Преобразование столбца 'Месяц' в тип datetime
    df['Дата'] = pd.to_datetime(df['Дата'], format='%Y-%m')

    df['Дата'] = df['Дата'].dt.strftime('%Y-%m')
    if (file_type.__contains__('csv')):
        if (df.iloc[0]['Цена нефти, $'].__contains__(',')):
            df['Цена нефти, $'] = df['Цена нефти, $'].str.replace(',', '.').astype(float)
        else:
            df['Цена нефти, $'] = df['Цена нефти, $'].astype(float)
    return df


def AnalizRyada(file_content, file_type, period):
    k = 0.6  # Коэффициент сглаживания
    b = 0.7  # Коэффициент тренда
    p = period  # Период
    df = process_file(file_content, file_type)
    end_date = df['Дата'].max()
    for l in range(1, p + 1):
        listT = [0]  # Значение тренда
        listY = list()  # Создаем лист значений датафрейма  с ценами на нефть
        listL = list()  # Создаем лист значений эскпоненциально сглаженного ряда
        DateList = list()  # Создаем лист дат
        kolichestvo = len(df) - 1  # Количество записей
        ### Заполнение листов с ценами на нефть и датами
        for j in range(kolichestvo, -1, -1):
            listY.append(df.iloc[j]['Цена нефти, $'])
            DateList.append(df.iloc[j]['Дата'])
        ###
        listL.append(listY[0])  # Первое значение сглаженного ряда = Первому значению ряда

        ### Функция добавления новой даты
        def GetDate():
            dateSplit = DateList[len(DateList) - 1].split('-')
            month = int(dateSplit[1])
            year = int(dateSplit[0])
            if (month < 12 and int(dateSplit[len(dateSplit) - 1]) > 0):
                month = month + 1
                if (month < 10):
                    monthS = '0' + str(month)
                else:
                    monthS = str(month)
            elif (month == 12):
                year = year + 1
                monthS = '01'
            return str(year) + "-" + monthS

        ###

        ### Заполнение экспоненциально-сглаженного ряда и Тренда
        for i in range(1, kolichestvo - 1):
            L = k * listY[i] + (1 - k) * (listL[i - 1] - listT[i - 1])
            listL.append(round(L, 2))
            T = b * (listL[i] - listL[i - 1]) + (1 - b) * listT[i - 1]
            listT.append(round(T, 2))
        ###

        # Добавление в ряд нового спрогнозированного значения
        new_row = pd.DataFrame(
            {'Дата': [GetDate()], 'Цена нефти, $': [round(listL[len(listL) - 1] + k * listT[len(listT) - 1], 2)]})

        # Добавление новой строки в датафрейм с помощью метода concat()
        df = pd.concat([df, new_row], ignore_index=True)

        ### Сортировка для добавления нового значения в начало
        df['Дата'] = pd.to_datetime(df['Дата'], format='%Y-%m')
        df['Дата'] = df['Дата'].dt.strftime('%Y-%m')
        df['Цена нефти, $'] = df['Цена нефти, $'].astype(float)
        df = df.sort_values('Дата', ascending=False)
        df.reset_index(drop=True, inplace=True)

        ###

        ## Рассчитывание точности прогноза
        def TochbostAnaliza():
            dif_prognoz_and_error = 0
            for ij in range(1, len(listT)):
                prognoz_na_period = listL[ij - 1] + listT[ij - 1]
                model_error = listY[ij] - prognoz_na_period
                dif_prognoz_and_error += round((model_error * model_error) / (listY[ij] * listY[ij]), 3)
            return (1 - (dif_prognoz_and_error / (len(listY) - 1)))
        ###
    print(str(round(TochbostAnaliza(), 2) * 100) + '%')
    print(df)
    return df, end_date


@app.get("/")
async def root():
        return FileResponse("../fastApiProject1/static/index.html")

# для принятия файла
@app.post("/file/upload-file")
async def upload_file_and_open_in_pandas(file: UploadFile = File(...)):
    file_content = await file.read()  # Чтение содержимого файла в память
    file_type = file.content_type

    df = process_file(file_content, file_type)
    fig = px.line(df, x='Дата', y='Цена нефти, $', markers=True, title='График цены нефти по датам',
                      labels={'Цена нефти, $': 'Цена нефти в долларах'})
    # Отображение интерактивного графика без открытия в браузере
    fig_json = fig.to_json()
    return JSONResponse(content=fig_json)



# для принятия файла
@app.post("/file/analiz-file")
async def analyze_file(numericInput: int = Form(...), file: UploadFile = File(...)):
    file_content = await file.read()  # Чтение содержимого файла в память
    file_type = file.content_type
    period = numericInput
    ds, end_date = AnalizRyada(file_content, file_type, period)
    filtered_data = ds[ds['Дата'] >= end_date]
    ds['Цвет'] = ['red' if date <= end_date else 'blue' for date in ds['Дата']]

    figi = px.line(ds, x='Дата', y='Цена нефти, $', markers=True, title='График цены нефти по датам11',
              labels={'Цена нефти, $': 'Цена нефти в долларах'}, color='Цвет')
    # Отображение интерактивного графика без открытия в браузере
    figi_json = figi.to_json()
    return JSONResponse(content=figi_json)


# @app.post("/file/period")
# async def period(numberInput: int = Form(...)):
#         global saved_number
#         saved_number = numberInput
#         return {"received_value": numberInput}
#
# @app.get("/get_saved_number")
# async def get_saved_number():
#     return {"saved_number": saved_number}
#

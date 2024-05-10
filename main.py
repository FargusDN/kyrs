import pandas as pd
import matplotlib.pyplot as plt

df = pd.read_csv('Urals.csv', delimiter=';')
df.dropna(inplace=True)



df[['Год', 'Месяц']] = df['Год, месяц'].str.split(', ', expand=True)

df = df.drop('Год, Месяц', axis=1)
print(df)

print(df)
# Построим график продаж
plt.plot(df['Год, месяц'], df['Цена нефти Urals, $'])
plt.title('Продажи в магазине МВидео')
plt.xlabel('Год, месяц')
plt.ylabel('Цена нефти Urals, $')
plt.show()
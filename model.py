#Подключаем библиотеки

import os
import csv
import numpy as np
import tensorflow as tf
import pandas as pd
from tensorflow.keras.applications import EfficientNetV2S
# from tensorflow.keras.applications import EfficientNetV2L
from tensorflow.keras.models import Sequential, Model
from tensorflow.keras.layers import Dense, Flatten
from tensorflow.keras.layers import Dropout, GlobalAveragePooling2D
from tensorflow.keras.layers.experimental.preprocessing import Normalization
from tensorflow.keras.optimizers import Adam
from tensorflow.keras import utils
from tensorflow.keras.preprocessing import image
from tensorflow.keras.utils import image_dataset_from_directory
import cv2
import matplotlib.pyplot as plt
from google.colab import files
from google.colab import drive
from os import listdir
from os import path
%matplotlib inline 

# Загружаем тренировочные и тестовые данные


# Подключаемся к своему google диску

drive.mount('/content/drive')

# Загружаем данные с диска в локальные файлы

!cp -r ./drive/MyDrive/data_c/public_attach.zip ./public_attach.zip

# Распаковываем данные

!unzip ./public_attach.zip

!unzip ./public_attach/enface.zip
!unzip ./public_attach/profile.zip
!unzip ./public_attach/test.zip

# Создаём папку train и перемещаем в неё тренировочные данные

!mkdir ./train
!mv ./enface ./train/enface
!mv ./profile ./train/profile

# Если нужно полностью удалить какую-то папку, то используем !rm -rf

# !rm -rf ./sample_data

# Загрузка данных с dropbox (или ещё откуда-то, если открыть доступ)

# !wget https://www.dropbox.com/s/wajkanzja6py6n1/test.zip?dl=0 -O test_data.zip

# Создаём датасеты

train_dataset = image_dataset_from_directory('train',
                                             subset='training',
                                             seed=42,
                                             validation_split=0.1,
                                             batch_size=128,
                                             image_size=(128, 128))

validation_dataset = image_dataset_from_directory('train',
                                             subset='validation',
                                             seed=42,
                                             validation_split=0.1,
                                             batch_size=128,
                                             image_size=(128, 128))

# Смотрим названия классов

class_names = train_dataset.class_names
class_names

# Смотрим примеры данных из каждого датасета

plt.figure(figsize=(10, 10))
for images, labels in train_dataset.take(1):
  for i in range(10,19):
    ax = plt.subplot(3, 3, i - 9)
    plt.imshow(images[i].numpy().astype("uint8"))
    plt.title(class_names[labels[i]])
    plt.axis("off")

# Делаем AUTOTUNE на все датасеты

AUTOTUNE = tf.data.experimental.AUTOTUNE

train_dataset = train_dataset.prefetch(buffer_size=AUTOTUNE)
validation_dataset = validation_dataset.prefetch(buffer_size=AUTOTUNE)

# Создаём нейросеть

# Выбираем предобученную сеть

effficient_net = EfficientNetV2S(weights='imagenet', 
                                 include_top=False, 
                                 input_shape=(128, 128, 3))

# Делаем так, чтобы сама предобученная сеть не обучалась ещё раз

effficient_net.trainable = False

# Создаём свёрточные слои сети

model = Sequential()
model.add(Normalization())
# Добавляем модель effficient_net в сеть как слой
model.add(effficient_net)
model.add(Flatten())
model.add(Dense(512, activation='relu'))
model.add(Dropout(0.5))
model.add(Dense(1, activation='sigmoid'))
# relu + softmax - accuracy 0.49 - softmax не используем
# relu + sigmoid - accuracy 0.99
# tanh + sigmoid - accuracy 0.99

'''
x = effficient_net.output
x = GlobalAveragePooling2D()(x)
x = Dense(512, activation='relu')(x)
x = Dropout(0.2)(x)
predictions = Dense(1, activation='sigmoid')(x)
model = Model(inputs=effficient_net.input, outputs=predictions)
Работает хуже
'''

# Компилируем модель

model.compile(loss='binary_crossentropy',
              optimizer="RMSProp",
              metrics=['accuracy'])
# Оптимизаторы:
# adam - 0.992 (195.3 балла)
# adagrad - 0.9926 (197.2 балла)
# sgd - 0.9930 (197.2 балла)
# RMSProp - 0.9955 (197.9 балла)

# Обучаем модель

history = model.fit(train_dataset, 
                    validation_data=validation_dataset,
                    epochs=4)

# Смотрим графики точности и ошибки

plt.plot(history.history['accuracy'], 
         label='Доля верных ответов на обучающем наборе')
plt.plot(history.history['val_accuracy'], 
         label='Доля верных ответов на проверочном наборе')
plt.xlabel('Эпоха обучения')
plt.ylabel('Доля верных ответов')
plt.legend()
plt.show()

plt.plot(history.history['loss'], 
         label='Ошибка на обучающем наборе')
plt.plot(history.history['val_loss'], 
         label='Ошибка на проверочном наборе')
plt.xlabel('Эпоха обучения')
plt.ylabel('Ошибка')
plt.legend()
plt.show()

# Делаем предсказания для тестового набора данных

names = []
predictions = []
for dirname, _, filenames in os.walk('test'):
    img_resized_list = []
    k = 0
    n = 0
    for filename in filenames:
      path = os.path.join(dirname, filename)
      img = cv2.imread(path, cv2.IMREAD_UNCHANGED)
      #img = tf.keras.utils.load_img(path, target_size=(250, 250))
      img_resized = cv2.resize(img, (128, 128), interpolation = cv2.INTER_AREA)
      #img_reshaped = np.reshape(img_resized, (None, 128, 128, 3))
      img_array = tf.expand_dims(tf.keras.utils.img_to_array(img_resized), 0)
      img_resized_list.append(img_array)
      names.append(filename)
      n += 1
      k += 1
      if k == 128:
        k = 0
        dataset = tf.data.Dataset.from_tensor_slices(img_resized_list)
        pred = model.predict(dataset)
        for p in pred:
          predictions.append(p)
        img_resized_list = []
      print(n)
      #print(os.path.join(dirname, filename))
dataset = tf.data.Dataset.from_tensor_slices(img_resized_list)
pred = model.predict(dataset)
for p in pred:
  predictions.append(p)
  img_resized_list = []
print(names[0], predictions[0])

# Переводим предсказания в целые числа

answer = []
for i in predictions:
  if i < 0.5:
    answer.append(0)
  else:
    answer.append(1)
answer

# Убираем пробелы из начала названий картинок

filenames = [] # итоговые названия файлов
for i in names:
  filenames.append(i[1:])
filenames

# Сверяем длины обоих списков

print(len(filenames))
print(len(answer))

# Переводим ответы в DataFrame

d = {'filename': filenames, 'label': answer}
df = pd.DataFrame(data=d)
df

# Сортируем df по возрастанию номеров картинок

sort_val = [] # столбец с номерами нартинов в числовом формате 
for i in df['filename']:
  sort_val.append(int(i[:-4]))
df['sort_val'] = sort_val
df

df.sort_values('sort_val')

# Но вообще, можно ничего и не сортировать. Всё равно оказалось, что файл скачивается несортированный

# Создаём файл с ответами и скачиваем его

submission = df.to_csv('submission.csv', index=False, sep=',')

files.download('submission.csv')

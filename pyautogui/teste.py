import pyautogui
import time

pyautogui.PAUSE = 2
user ='user'
pyautogui.press('winleft')
pyautogui.write('firefox')
pyautogui.press('enter')
time.sleep(0)
pyautogui.write('https://wwww.facebook.com/')

pyautogui.press('enter')
time.sleep(3)
pyautogui.write(user)
time.sleep(0)
pyautogui.press('tab')
pyautogui.write('pass')
pyautogui.press('enter')




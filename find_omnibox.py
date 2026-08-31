import uiautomation as auto
import time

print("Через 5 секунд переключись на Яндекс.Браузер...")
time.sleep(5)

win = auto.GetForegroundControl()

if not win:
    print("Окно не найдено")
    raise SystemExit

print(f"Окно: {win.Name}")

control = win.Control(
    ClassName="SmartboxEditField",
    searchDepth=20
)

if not control.Exists(1):
    print("SmartboxEditField не найден")
    raise SystemExit

print("\nНашли SmartboxEditField:")
print("Class:", control.ClassName)
print("AutomationId:", control.AutomationId)
print("Name:", control.Name)

print("\nПробуем ValuePattern:")
try:
    p = control.GetValuePattern()
    print("Pattern:", p)
    print("Value:", repr(p.Value if p else None))
except Exception as e:
    print("ERROR:", repr(e))

print("\nПробуем LegacyIAccessible:")
try:
    p = control.GetLegacyIAccessiblePattern()
    print("Pattern:", p)
    if p:
        print("Name:", repr(p.Name))
        print("Value:", repr(p.Value))
        print("Description:", repr(p.Description))
except Exception as e:
    print("ERROR:", repr(e))

print("\nПробуем TextPattern:")
try:
    p = control.GetTextPattern()
    print("Pattern:", p)
    if p:
        print("Text:", repr(p.GetText()))
except Exception as e:
    print("ERROR:", repr(e))
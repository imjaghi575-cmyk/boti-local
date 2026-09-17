from __future__ import annotations
import ast, json, operator, os, re, tempfile
from datetime import datetime
from pathlib import Path
MEMORY_FILE=Path(__file__).resolve().parent.parent/'data'/'memory.json'
MAX_INPUT_LENGTH=2000; MAX_MEMORY_ITEMS=100; MAX_NAME_LENGTH=80; MAX_MEMORY_TEXT_ITEMS=10
OPS={ast.Add:operator.add,ast.Sub:operator.sub,ast.Mult:operator.mul,ast.Div:operator.truediv,ast.FloorDiv:operator.floordiv,ast.Mod:operator.mod,ast.Pow:operator.pow}; UOPS={ast.UAdd:operator.pos,ast.USub:operator.neg}
def normalize(text:str)->str:
 if not isinstance(text,str): return ''
 text=text.translate(str.maketrans('يىكۀةؤإأٱ۰۱۲۳۴۵۶۷۸۹','ییکههوااا۰۱۲۳۴۵۶۷۸۹'))
 text=re.sub(r'[\u200b\u200c\u200d\ufeff]',' ',text)
 return re.sub(r'\s+',' ',text.strip().casefold())
def _safe_calculate(expression:str)->int|float:
 if not expression or len(expression)>80 or not re.fullmatch(r'[0-9+\-*/%.() ]+',expression): raise ValueError
 def visit(n):
  if isinstance(n,ast.Expression): return visit(n.body)
  if isinstance(n,ast.Constant) and isinstance(n.value,(int,float)) and not isinstance(n.value,bool):
   if abs(n.value)>10**12 or not (-float('inf')<n.value<float('inf')): raise ValueError
   return n.value
  if isinstance(n,ast.UnaryOp) and type(n.op) in UOPS: result=UOPS[type(n.op)](visit(n.operand))
  elif isinstance(n,ast.BinOp) and type(n.op) in OPS:
   a,b=visit(n.left),visit(n.right)
   if isinstance(n.op,ast.Pow) and abs(b)>10: raise ValueError
   result=OPS[type(n.op)](a,b)
  else: raise ValueError
  if not isinstance(result,(int,float)) or abs(result)>10**15 or not (-float('inf')<result<float('inf')): raise ValueError
  return result
 return visit(ast.parse(expression,mode='eval'))
class LocalBot:
 def __init__(self): MEMORY_FILE.parent.mkdir(parents=True,exist_ok=True); self.memory=self._load_memory()
 def _load_memory(self):
  if not MEMORY_FILE.exists(): return []
  try:
   data=json.loads(MEMORY_FILE.read_text(encoding='utf-8')); valid=[]
   if not isinstance(data,list): return []
   for x in data[-MAX_MEMORY_ITEMS:]:
    if not isinstance(x,dict): continue
    if x.get('fact')=='name' and isinstance(x.get('value'),str) and x['value'].strip(): valid.append({'fact':'name','value':x['value'].strip()[:MAX_NAME_LENGTH],'time':str(x.get('time',''))[:40]})
    elif isinstance(x.get('user'),str) and isinstance(x.get('bot'),str): valid.append({'user':x['user'][:MAX_INPUT_LENGTH],'bot':x['bot'][:MAX_INPUT_LENGTH],'time':str(x.get('time',''))[:40]})
   return valid[-MAX_MEMORY_ITEMS:]
  except (json.JSONDecodeError,OSError,UnicodeError,TypeError): return []
 def _save_memory(self):
  fd,name=tempfile.mkstemp(prefix='memory-',suffix='.tmp',dir=MEMORY_FILE.parent)
  try:
   with os.fdopen(fd,'w',encoding='utf-8') as f: f.write(json.dumps(self.memory[-MAX_MEMORY_ITEMS:],ensure_ascii=False,indent=2)); f.flush(); os.fsync(f.fileno())
   os.chmod(name,0o600); os.replace(name,MEMORY_FILE)
  except OSError:
   try: os.unlink(name)
   except OSError: pass
 def _remember(self,text,answer): self.memory=(self.memory+[{'user':text[:MAX_INPUT_LENGTH],'bot':answer[:MAX_INPUT_LENGTH],'time':datetime.now().isoformat(timespec='seconds')}])[-MAX_MEMORY_ITEMS:]; self._save_memory()
 def clear_memory(self): self.memory=[]; self._save_memory()
 def stats(self): return f'تعداد موارد حافظه: {len(self.memory)} از {MAX_MEMORY_ITEMS}'
 def _saved_name(self): return next((x['value'] for x in reversed(self.memory) if x.get('fact')=='name' and x.get('value')),None)
 def _answer_for_math(self,value):
  m=re.search(r'(?:حساب کن|محاسبه کن|جواب)\s*[:：]?\s*(.*)$',value)
  if not m:return None
  try:
   r=_safe_calculate(m.group(1).strip()); return f'نتیجه: {r:g}' if isinstance(r,float) else f'نتیجه: {r}'
  except (ValueError,SyntaxError,ZeroDivisionError,OverflowError,MemoryError,RecursionError): return 'این عبارت ریاضی قابل محاسبه نیست.'
 def reply(self,text):
  original=str(text).strip()[:MAX_INPUT_LENGTH]; value=normalize(original); now=datetime.now()
  if not value:return 'یک پیام بنویس تا پاسخ بدم.'
  m=re.fullmatch(r'(?:اسم|نام) من\s+(.+?)\s+(?:هست|است)$',value) or re.fullmatch(r'(?:اسم|نام) من\s*[:：-]\s*(.+)$',value) or re.fullmatch(r'(?:اسم|نام) من\s+(?:این است)\s+(.+)$',value)
  if m:
   name=m.group(1).strip(' .،,!؟')[:MAX_NAME_LENGTH]
   if not name or name in {'چیه','چیست','چی','؟','?'}: return 'اسم را کامل بنویس؛ مثلاً: اسم من علی است.'
   answer=f'خوشحالم که شناختیمت، {name}! این مورد را محلی ذخیره کردم.'; self.memory=[x for x in self.memory if x.get('fact')!='name']+[{'fact':'name','value':name,'time':now.isoformat(timespec='seconds')}]; self.memory=self.memory[-MAX_MEMORY_ITEMS:]; self._save_memory(); return answer
  answer=self._answer_for_math(value)
  if answer is None:
   if any(x in value for x in ('اسم من چیه','نام من چیه','من کی هستم')): n=self._saved_name(); answer=f'اسم تو {n} است.' if n else 'هنوز اسمت را به من نگفتی.'
   elif any(x in value for x in ('سلام','درود','hello','hi','خسته نباشی')): n=self._saved_name(); answer=f'سلام {n}! 🌷 من بوتی هستم.' if n else 'سلام! 🌷 من بوتی هستم. آماده‌ام کمکت کنم.'
   elif any(x in value for x in ('اسمت چیه','نامت چیه','تو کی هستی','خودت رو معرفی')): answer='من بوتی هستم؛ دستیار محلی و آفلاین برای Termux.'
   elif 'ساعت' in value or 'زمان' in value: answer=f'ساعت سیستم: {now:%H:%M:%S}'
   elif 'تاریخ' in value or 'امروز' in value: answer=f'تاریخ سیستم: {now:%Y-%m-%d}'
   elif 'یادت' in value or 'حافظه' in value: answer=self.memory_text()
   elif 'کمک' in value or 'قابلیت' in value or 'چه کار' in value: answer='قابلیت‌ها: گفت‌وگوی پایه، نام، حافظه، محاسبه امن، زمان و تاریخ.'
   elif any(x in value for x in ('ممنون','مرسی','سپاس')): answer='خواهش می‌کنم! 😊'
   elif 'خوبی' in value or 'حالت چطوره' in value: answer='خوبم و آماده‌ام! تو چطوری؟'
   else: answer='پیامت دریافت شد. می‌توانی سؤال مشخص بپرسی یا بنویسی «حساب کن: ۱۲ + ۸».'
  self._remember(original,answer); return answer
 def memory_text(self):
  if not self.memory:return 'حافظه هنوز خالی است.'
  lines=[f'حافظه محلی ({min(MAX_MEMORY_TEXT_ITEMS,len(self.memory))} مورد آخر):']
  for x in self.memory[-MAX_MEMORY_TEXT_ITEMS:]: lines.append(f"- نام ذخیره‌شده: {x.get('value','')}" if x.get('fact')=='name' else f"- شما: {x.get('user','')}\n  بات: {x.get('bot','')}")
  return '\n'.join(lines)

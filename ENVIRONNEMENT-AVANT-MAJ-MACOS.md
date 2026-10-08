# Empreinte de l'environnement DFM

Prise le 14 août 2026, juste avant la mise à jour macOS 15.1 → 26.2.
Sert à remettre DFM en marche si la mise à jour casse quelque chose.

## Système avant mise à jour
```
ProductName:		macOS
ProductVersion:		15.1
BuildVersion:		24B2083
```

## Python utilisé par le venv
```
Python 3.13.14
chemin réel :
/Library/Frameworks/Python.framework/Versions/3.13
```

## Python présents sur le système
```
/Library/Frameworks/Python.framework/Versions/3.13/bin/python3
/usr/local/bin/python3
/usr/bin/python3
```

## Paquets installés dans le venv
```
annotated-types==0.7.0
anyio==4.12.1
blinker==1.9.0
certifi==2026.6.17
cffi==2.0.0
charset-normalizer==3.4.9
click==8.1.8
compact-json==1.8.2
cramjam==2.11.0
cryptography==49.0.0
deprecation==2.1.0
enum-tools==0.13.0
exceptiongroup==1.3.1
Flask==3.1.3
google-api-core==2.30.3
google-api-python-client==2.198.0
google-auth==2.50.0
google-auth-httplib2==0.3.1
google-auth-oauthlib==1.3.1
googleapis-common-protos==1.75.0
h11==0.16.0
h2==4.4.0
hpack==4.2.0
httpcore==1.0.9
httplib2==0.32.0
httpx==0.28.1
hyperframe==6.1.0
idna==3.18
importlib_metadata==8.7.1
importlib_resources==7.1.0
itsdangerous==2.2.0
Jinja2==3.1.6
MarkupSafe==3.0.3
multidict==6.7.1
numbers-parser==4.19.0
oauthlib==3.3.1
packaging==26.2
postgrest==2.31.0
propcache==0.4.1
proto-plus==1.27.2
protobuf==7.35.1
pyasn1==0.6.4
pyasn1_modules==0.4.2
pycparser==2.23
pydantic==2.13.4
pydantic_core==2.46.4
Pygments==2.20.0
PyJWT==2.13.0
pymupdf==1.28.0
pyparsing==3.3.2
pypdf==6.14.2
python-dateutil==2.9.0.post0
python-snappy==0.7.3
realtime==2.31.0
requests==2.32.5
requests-oauthlib==2.0.0
setuptools==83.0.0
sigfig==1.3.19
six==1.17.0
sortedcontainers==2.4.0
storage3==2.31.0
StrEnum==0.4.15
supabase==2.31.0
supabase-auth==2.31.0
supabase-functions==2.31.0
typing-inspection==0.4.2
typing_extensions==4.16.0
uritemplate==4.2.0
urllib3==2.6.3
wcwidth==0.8.2
websockets==15.0.1
Werkzeug==3.1.8
yarl==1.22.0
zipp==3.23.1
```

## Remise en marche si le venv est cassé

```bash
cd ~/Desktop/DFM
rm -rf venv
python3 -m venv venv
./venv/bin/pip install -r <paquets listés ci-dessus>
```

Le lanceur DFM.command bascule tout seul sur /usr/bin/python3 si le venv
disparaît — mais Flask n'y est pas forcément installé, d'où cette fiche.

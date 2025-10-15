# kabka - Kabyle and Georgian collision scanner

Quickly check how web sites react to Occitan (`oci`) and Kabyle (`kab`) language headers.

## Install & run

### 1. clone or download the repo

```bash
git clone https://github.com/BoFFire/kabka.git
```

```bash
cd kabka
```

### 2. create a virtual environment
```bash
python3 -m venv venv
```

```bash
source venv/bin/activate
```

### 3. install dependencies

```bash
pip install -r requirements.txt
```

### 4. scan a single site interactively

```bash
python kabka.py
```

### 5. or generate the full Occitan & Kabyle report

```bash
python kabka.py --report
```

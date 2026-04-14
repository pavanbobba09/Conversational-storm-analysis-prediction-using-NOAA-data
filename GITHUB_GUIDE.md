# GitHub Upload Guide

**What to Include and Exclude from GitHub**

---

## ✅ Files TO INCLUDE (Safe to Commit)

### Code Files
- ✅ `src/` - All Python source code
- ✅ `requirements.txt` - Python dependencies
- ✅ `README.md` - Project documentation
- ✅ `.gitignore` - Git ignore rules
- ✅ `.env.example` - Environment template (NO ACTUAL KEYS)

### Configuration
- ✅ `schema/create_tables.sql` - Database schema
- ✅ All `.md` documentation files (README, SETUP guides)
- ✅ `documentation/` folder - All markdown docs

### Scripts
- ✅ All Python scripts in `src/`
- ✅ Setup and installation scripts

---

## ❌ Files TO EXCLUDE (DO NOT Commit)

### 1. Large Data Files 🚫 NEVER COMMIT

**Why:** GitHub has a 100MB file size limit. Data files are huge.

```
❌ dataset/                           # 32 CSV files (~2GB total)
❌ data/processed/*.parquet           # Processed data files (500MB+)
❌ data/geocoding/*.json              # Geocoding database
❌ *.csv                              # Any CSV files
❌ *.parquet                          # Any parquet files
```

**What to do instead:**
- Document where to download NOAA data
- Provide download links in README
- Include data processing scripts (these ARE committed)

---

### 2. API Keys & Secrets 🔐 CRITICAL - NEVER COMMIT

**Why:** Public GitHub repos expose your API keys to the world!

```
❌ .env                               # Contains GROQ_API_KEY
❌ .env.local                         # Local environment variables
```

**What to do instead:**
- ✅ Commit `.env.example` (template with placeholders)
- Include setup instructions for users to create their own `.env`

**Example `.env.example`:**
```bash
# Copy this to .env and add your actual keys
GROQ_API_KEY=your_groq_api_key_here
QUERY_BACKEND=postgresql
DB_HOST=localhost
DB_PORT=5432
DB_NAME=noaa_storms
DB_USER=postgres
DB_PASSWORD=your_password_here
```

---

### 3. Database Files 🗄️ DO NOT COMMIT

**Why:** Database dumps are large and may contain sensitive data.

```
❌ *.sql.gz                           # Compressed SQL dumps
❌ *.dump                             # PostgreSQL dumps
❌ *.backup                           # Database backups
❌ *.db, *.sqlite, *.sqlite3          # SQLite files
```

**What to do instead:**
- Provide migration scripts (✅ committed)
- Document how to set up database
- Provide schema files (✅ committed)

---

### 4. Generated Files 📁 DO NOT COMMIT

**Why:** These are created by the application and can be regenerated.

```
❌ exports/                           # Excel exports from queries
❌ *.xlsx                             # Excel files
❌ __pycache__/                       # Python cache
❌ *.pyc, *.pyo                       # Compiled Python
❌ flagged/                           # Gradio cached examples
❌ *.log                              # Log files
❌ tmp/, temp/                        # Temporary files
```

---

### 5. Virtual Environment 🐍 DO NOT COMMIT

**Why:** Virtual environments are large and OS-specific.

```
❌ venv/                              # Virtual environment
❌ env/                               # Alternative venv name
❌ .venv/                             # Hidden venv
```

**What to do instead:**
- ✅ Commit `requirements.txt`
- Users create their own venv: `python -m venv venv`

---

### 6. IDE & OS Files 💻 DO NOT COMMIT

**Why:** These are personal preferences and OS-specific.

```
❌ .vscode/                           # VS Code settings
❌ .idea/                             # PyCharm settings
❌ .DS_Store                          # macOS folder settings
❌ Thumbs.db                          # Windows thumbnails
❌ *.swp, *.swo                       # Vim swap files
```

---

### 7. Trained Models 🤖 DO NOT COMMIT (if applicable)

**Why:** ML models are very large files.

```
❌ models/*.pkl                       # Pickle files
❌ models/*.h5                        # Keras models
❌ models/*.pt, *.pth                 # PyTorch models
```

**Note:** This project doesn't use trained models (retrieval, not prediction), but included for completeness.

---

## 📋 Quick Check Before Committing

Run this command to see what you're about to commit:

```bash
git status
```

**Red flags - DO NOT commit if you see:**
- ❌ `.env` file
- ❌ Files in `dataset/` folder
- ❌ Files in `data/processed/`
- ❌ Files in `venv/` folder
- ❌ `*.parquet` or `*.csv` files
- ❌ Files over 50MB

**Green light - Safe to commit:**
- ✅ Files in `src/` directory
- ✅ `requirements.txt`
- ✅ `README.md` and other `.md` files
- ✅ `.gitignore`
- ✅ `.env.example`
- ✅ `schema/*.sql`

---

## 🚀 Git Commands for First Upload

### Step 1: Initialize Git (if not already done)

```bash
cd /Users/pavanbobba/Documents/master\'s_Project/postgresql/Conversational-storm-analysis-prediction-using-NOAA-data

git init
```

### Step 2: Add Remote Repository

```bash
# Replace with your actual GitHub repo URL
git remote add origin https://github.com/yourusername/your-repo-name.git
```

### Step 3: Check What Will Be Committed

```bash
git status
```

**Verify:**
- No `.env` file listed
- No large data files
- Only code and documentation

### Step 4: Add Files

```bash
# Add all files (gitignore will exclude unwanted files)
git add .

# Or add specific files
git add src/
git add requirements.txt
git add README.md
git add .gitignore
git add documentation/
git add schema/
```

### Step 5: Check File Sizes

```bash
# See files that will be committed and their sizes
git ls-files | xargs ls -lh

# If any file is over 50MB, add it to .gitignore
```

### Step 6: Commit

```bash
git commit -m "Initial commit: NOAA Storm Analytics System with PostgreSQL"
```

### Step 7: Push to GitHub

```bash
# First time push
git push -u origin main

# Or if your default branch is master
git push -u origin master
```

---

## ⚠️ If You Accidentally Commit Sensitive Files

### Remove .env file from Git (if committed by mistake)

```bash
# Remove from Git but keep local file
git rm --cached .env

# Commit the removal
git commit -m "Remove .env file from version control"

# Push
git push
```

### Remove large file from Git history

```bash
# Remove file from all commits (use with caution!)
git filter-branch --force --index-filter \
  "git rm --cached --ignore-unmatch path/to/large/file.csv" \
  --prune-empty --tag-name-filter cat -- --all

# Force push (DANGEROUS - rewrites history)
git push --force
```

**Better approach:** Start fresh if you committed secrets:
1. Delete the GitHub repository
2. Create a new one
3. Commit only safe files

---

## 📊 Repository Size Guidelines

**Good repository size:** < 100MB
**Acceptable:** 100MB - 500MB
**Too large:** > 500MB (will have issues)

**Your repository without data files:** ~5-10MB ✅
**Your repository with data files:** ~2.5GB ❌ TOO BIG

This is why `.gitignore` excludes data files!

---

## 🔍 Verify .gitignore is Working

```bash
# Test: Check if data files are ignored
git check-ignore dataset/StormEvents_details-*.csv

# Expected output: Lists the ignored files

# Check what will be committed
git add -n .

# Expected: Only code files, no data or .env files
```

---

## 📝 What Your GitHub Repo Should Contain

```
your-repo/
├── .gitignore                    ✅ Ignore rules
├── .env.example                  ✅ Environment template
├── README.md                     ✅ Project overview
├── requirements.txt              ✅ Dependencies
├── SETUP_API_KEY.md             ✅ Setup guide
├── QUICKSTART.md                ✅ Quick start guide
│
├── documentation/               ✅ All .md files
│   ├── HOW_IT_WORKS.md
│   ├── PRESENTATION_GUIDE.md
│   ├── PROJECT_ARCHITECTURE.md
│   └── SYSTEM_FLOW_DIAGRAM.md
│
├── schema/                      ✅ Database schema
│   └── create_tables.sql
│
├── src/                         ✅ All source code
│   ├── analytics/
│   ├── chatbot/
│   ├── data/
│   ├── database/
│   └── interfaces/
│
├── notebooks/                   ✅ Jupyter notebooks (optional)
│   └── *.ipynb
│
└── tests/                       ✅ Test files (if created)
    └── *.py
```

**NOT included (excluded by .gitignore):**
- ❌ dataset/ - 2GB of CSV files
- ❌ data/processed/ - 500MB parquet files
- ❌ venv/ - Virtual environment
- ❌ .env - API keys
- ❌ exports/ - Generated Excel files
- ❌ __pycache__/ - Python cache

---

## 🎯 README.md Should Explain Data Setup

Add this to your README.md:

```markdown
## Data Setup

This project uses NOAA Storm Events Database (1996-2025).

### Download Data

1. Visit: https://www.ncdc.noaa.gov/stormevents/
2. Download CSV files for years 1996-2025
3. Place in `dataset/` folder

Or use the provided data loader:

```bash
python src/data/loader.py
python src/data/cleaner.py
```

### Database Setup

1. Install PostgreSQL 17
2. Create database: `createdb noaa_storms`
3. Run migration: `python src/database/migrate_to_postgres.py`

See `QUICKSTART.md` for detailed instructions.
```

---

## ✅ Final Checklist Before Push

- [ ] `.env` is NOT in the commit (check with `git status`)
- [ ] No files over 50MB (check with `git ls-files | xargs ls -lh`)
- [ ] No `dataset/` or `data/processed/` files
- [ ] `requirements.txt` is up to date
- [ ] `.env.example` exists with placeholders
- [ ] README.md has data setup instructions
- [ ] All API keys are removed from code
- [ ] `.gitignore` is properly configured

---

## 🔒 Security Best Practices

1. **Never commit `.env` files**
2. **Use environment variables** for all secrets
3. **Review commits** before pushing (`git diff --staged`)
4. **Use `.env.example`** for templates
5. **Document setup** in README (without actual keys)
6. **Enable GitHub secrets scanning** (in repository settings)
7. **Use private repos** for sensitive projects
8. **Rotate API keys** if accidentally committed

---

## 📚 Additional Resources

- **GitHub File Size Limits**: https://docs.github.com/en/repositories/working-with-files/managing-large-files
- **gitignore Templates**: https://github.com/github/gitignore
- **Removing Sensitive Data**: https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/removing-sensitive-data-from-a-repository

---

**Summary:**
- ✅ Commit: Code, documentation, configuration templates
- ❌ Never commit: Data files, API keys, generated files, virtual environments

Your `.gitignore` is now configured to automatically exclude all unsafe files!

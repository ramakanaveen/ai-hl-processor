#!/usr/bin/env python3
"""
Setup Environment Configuration
Helper script to create .env file for the financial news analysis system
"""

import os
from pathlib import Path


def create_env_file():
    """Create .env file with user input"""

    print("=== Financial News Impact Analysis - Environment Setup ===\n")

    env_file = Path(".env")

    if env_file.exists():
        overwrite = input(".env file already exists. Overwrite? (y/N): ").lower().strip()
        if overwrite != 'y':
            print("Setup cancelled.")
            return

    print("Please provide the following information:\n")

    # Google Cloud Configuration
    print("1. Google Cloud Configuration:")
    project_id = input("   Google Cloud Project ID: ").strip()

    credentials_path = input("   Path to service account key JSON file: ").strip()
    if credentials_path and not os.path.exists(credentials_path):
        print(f"   Warning: File {credentials_path} not found!")

    # Environment
    print("\n2. Environment Configuration:")
    environment = input("   Environment (development/staging/production) [development]: ").strip() or "development"

    # Optional configurations
    print("\n3. Optional Database Configuration (press Enter to skip):")
    db_host = input("   Database Host [localhost]: ").strip() or "localhost"
    db_port = input("   Database Port [5432]: ").strip() or "5432"
    db_username = input("   Database Username [finance_user]: ").strip() or "finance_user"
    db_password = input("   Database Password: ").strip()
    db_name = input("   Database Name [financial_news_db]: ").strip() or "financial_news_db"

    print("\n4. Optional Redis Configuration (press Enter to skip):")
    redis_host = input("   Redis Host [localhost]: ").strip() or "localhost"
    redis_port = input("   Redis Port [6379]: ").strip() or "6379"

    # Create .env content
    env_content = f"""# Google Cloud Configuration
GOOGLE_CLOUD_PROJECT={project_id}
GOOGLE_CREDENTIALS_PATH={credentials_path}

# Environment Configuration
ENVIRONMENT={environment}

# Database Configuration
DB_HOST={db_host}
DB_PORT={db_port}
DB_USERNAME={db_username}
DB_PASSWORD={db_password}
DB_NAME={db_name}

# Redis Configuration
REDIS_HOST={redis_host}
REDIS_PORT={redis_port}

# Optional: Additional API Keys (uncomment and fill as needed)
# OPENAI_API_KEY=your-openai-api-key
# BLOOMBERG_API_KEY=your-bloomberg-api-key
# SENTRY_DSN=your-sentry-dsn
# JWT_SECRET_KEY=your-jwt-secret-key
# SLACK_WEBHOOK_URL=your-slack-webhook-url
"""

    # Write .env file
    with open(env_file, 'w') as f:
        f.write(env_content)

    print(f"\n✅ .env file created successfully!")
    print(f"📁 Location: {env_file.absolute()}")

    # Validation
    print("\n🔍 Validating configuration...")

    issues = []
    if not project_id:
        issues.append("Google Cloud Project ID is required")

    if not credentials_path:
        issues.append("Google credentials path is required for production use")
    elif not os.path.exists(credentials_path):
        issues.append(f"Credentials file not found: {credentials_path}")

    if issues:
        print("⚠️  Configuration issues found:")
        for issue in issues:
            print(f"   - {issue}")
        print("\nYou can fix these issues by editing the .env file manually.")
    else:
        print("✅ Configuration looks good!")

    print(f"\n🚀 Next steps:")
    print(f"   1. Install dependencies: pip install -r requirements-minimal.txt")
    print(f"   2. Test the system: python main.py demo")
    print(f"   3. Analyze news: python main.py analyze \"Your news headline here\"")


def verify_env_file():
    """Verify existing .env file configuration"""

    env_file = Path(".env")

    if not env_file.exists():
        print("❌ .env file not found. Run setup first.")
        return False

    print("🔍 Verifying .env configuration...\n")

    # Load .env file manually to check
    env_vars = {}
    with open(env_file, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                env_vars[key] = value

    required_vars = ['GOOGLE_CLOUD_PROJECT', 'GOOGLE_CREDENTIALS_PATH']
    optional_vars = ['ENVIRONMENT', 'DB_HOST', 'REDIS_HOST']

    print("Required variables:")
    all_good = True
    for var in required_vars:
        value = env_vars.get(var, '')
        status = "✅" if value else "❌"
        print(f"   {status} {var}: {value or 'NOT SET'}")
        if not value:
            all_good = False

    print("\nOptional variables:")
    for var in optional_vars:
        value = env_vars.get(var, '')
        status = "✅" if value else "⚪"
        print(f"   {status} {var}: {value or 'not set'}")

    # Check credentials file
    credentials_path = env_vars.get('GOOGLE_CREDENTIALS_PATH', '')
    if credentials_path:
        if os.path.exists(credentials_path):
            print(f"✅ Credentials file found: {credentials_path}")
        else:
            print(f"❌ Credentials file not found: {credentials_path}")
            all_good = False

    print(f"\n{'✅ Configuration verified!' if all_good else '❌ Configuration has issues.'}")
    return all_good


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Setup environment for financial news analysis")
    parser.add_argument('--verify', action='store_true', help='Verify existing .env file')

    args = parser.parse_args()

    if args.verify:
        verify_env_file()
    else:
        create_env_file()
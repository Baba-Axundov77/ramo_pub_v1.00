# Installation Guide

## Requirements

Python 3.10 or higher
PostgreSQL 12 or higher

## Step 1: PostgreSQL Setup

Ubuntu/Debian:
  sudo apt install postgresql postgresql-contrib

Windows:
  Download from https://www.postgresql.org/download/windows/

Create database:
  CREATE DATABASE ramo_pub;

## Step 2: Virtual Environment (recommended)

  python -m venv venv

  Windows: venv\Scripts\activate
  Linux/macOS: source venv/bin/activate

## Step 3: Install Packages

  pip install -r requirements.txt

Or manually:
  pip install SQLAlchemy psycopg2-binary python-dotenv
  pip install PyQt6
  pip install matplotlib
  pip install Pillow
  pip install Flask
  pip install reportlab

## Step 4: Configure

  copy .env.example .env    (Windows)
  cp .env.example .env      (Linux/macOS)

Edit .env and set your DB_PASSWORD.

## Step 5: Run

  Desktop: python main.py
  Web panel: python -m web.app

Login: admin / admin123

## Common Errors

psycopg2 install error on Linux:
  sudo apt install libpq-dev python3-dev
  pip install psycopg2-binary

PyQt6 install error on Linux:
  sudo apt install libgl1-mesa-glx libglib2.0-0
  pip install PyQt6

Cannot connect to database:
  Check DB_PASSWORD in .env file
  Make sure PostgreSQL is running:
  sudo systemctl status postgresql

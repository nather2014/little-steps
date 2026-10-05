package main

import (
	"context"
	"database/sql"
	"errors"
	"io"
	"strings"

	"golang.org/x/crypto/bcrypt"
)

// Operator-only command. It runs inside the server container, never over HTTP.
func resetPassword(ctx context.Context, db *sql.DB, email string, input io.Reader) error {
	raw, e := io.ReadAll(io.LimitReader(input, 74))
	if e != nil {
		return e
	}
	password := strings.TrimSuffix(strings.TrimSuffix(string(raw), "\n"), "\r")
	if len(password) < 8 || len(password) > 72 {
		return errors.New("New password must be 8–72 bytes")
	}
	hashed, e := bcrypt.GenerateFromPassword([]byte(password), bcrypt.DefaultCost)
	if e != nil {
		return e
	}
	tx, e := db.BeginTx(ctx, nil)
	if e != nil {
		return e
	}
	defer tx.Rollback()
	var id string
	e = tx.QueryRowContext(ctx, "UPDATE users SET password_hash=$1 WHERE email=$2 RETURNING id", string(hashed), strings.ToLower(strings.TrimSpace(email))).Scan(&id)
	if errors.Is(e, sql.ErrNoRows) {
		return errors.New("Account not found")
	}
	if e != nil {
		return e
	}
	if _, e = tx.ExecContext(ctx, "DELETE FROM auth_sessions WHERE user_id=$1", id); e != nil {
		return e
	}
	return tx.Commit()
}

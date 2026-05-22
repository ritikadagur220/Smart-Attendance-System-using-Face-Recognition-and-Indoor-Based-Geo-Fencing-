package com.smartattendance

import android.content.Intent
import android.os.Bundle
import android.util.Log
import android.widget.Button
import android.widget.EditText
import android.widget.TextView
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import com.google.firebase.auth.FirebaseAuth

class LoginActivity : AppCompatActivity() {

    companion object {
        private const val TAG = "LoginActivity"
    }

    private lateinit var auth: FirebaseAuth
    private lateinit var emailInput: EditText
    private lateinit var passwordInput: EditText
    private lateinit var loginButton: Button
    private lateinit var errorText: TextView

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_login)

        auth = FirebaseAuth.getInstance()

        emailInput = findViewById(R.id.editEmail)
        passwordInput = findViewById(R.id.editPassword)
        loginButton = findViewById(R.id.btnLogin)
        errorText = findViewById(R.id.textError)

        if (auth.currentUser != null) {
            navigateToMain()
            return
        }

        loginButton.setOnClickListener {
            performLogin()
        }
    }

    
    private fun performLogin() {
        val email = emailInput.text.toString().trim()
        val password = passwordInput.text.toString().trim()

        if (email.isEmpty()) {
            emailInput.error = "Email required"
            return
        }
        if (password.isEmpty()) {
            passwordInput.error = "Password required"
            return
        }

        loginButton.isEnabled = false
        loginButton.text = "Signing in..."
        errorText.text = ""

        auth.signInWithEmailAndPassword(email, password)
            .addOnCompleteListener(this) { task ->
                if (task.isSuccessful) {
                    Log.d(TAG, "signInWithEmail:success")
                    Toast.makeText(this, "Login successful!", Toast.LENGTH_SHORT).show()
                    navigateToMain()
                } else {
                    Log.w(TAG, "signInWithEmail:failure", task.exception)
                    errorText.text = task.exception?.message ?: "Authentication failed"
                    loginButton.isEnabled = true
                    loginButton.text = "Sign In"
                }
            }
    }

    
    private fun navigateToMain() {
        val intent = Intent(this, MainActivity::class.java)
        intent.flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TASK
        startActivity(intent)
        finish()
    }
}

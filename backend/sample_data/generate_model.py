import pandas as pd
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
import joblib
import os

# 1. Generate biased dataset
np.random.seed(42)
n_samples = 500

# Demographics
gender = np.random.choice(['Male', 'Female'], n_samples, p=[0.6, 0.4])
age = np.random.randint(20, 65, n_samples)

# Features with some correlation to demographics to introduce bias
income = np.where(gender == 'Male', 
                  np.random.normal(70000, 15000, n_samples), 
                  np.random.normal(56000, 12000, n_samples))
income = np.clip(income, 25000, 150000)

credit_score = np.random.normal(650, 50, n_samples)
# Older people tend to have slightly better credit scores
credit_score += (age - 30) * 1.5
credit_score = np.clip(credit_score, 300, 850)

employment_type = np.random.choice(['Full-time', 'Part-time', 'Self-employed'], n_samples, p=[0.7, 0.2, 0.1])
years_employed = np.random.randint(0, 20, n_samples)

# Generate biased target (loan_approved)
# Base probability
prob = np.zeros(n_samples)

# Bias: Male approval ~72%, Female ~38%
prob[gender == 'Male'] += 0.35
prob[gender == 'Female'] -= 0.1

# Bias: Age < 30 approval ~35%, Age > 45 approval ~68%
prob[age < 30] -= 0.15
prob[age > 45] += 0.2

# Add realistic factors
prob += (income - 50000) / 100000 * 0.2
prob += (credit_score - 600) / 250 * 0.4
prob += (years_employed / 20) * 0.1

# Sigmoid to bound between 0-1
prob = 1 / (1 + np.exp(-prob))

# Generate binary outcomes based on probabilities
loan_approved = (np.random.random(n_samples) < prob).astype(int)

df = pd.DataFrame({
    'age': age,
    'gender': gender,
    'income': income,
    'credit_score': credit_score,
    'employment_type': employment_type,
    'years_employed': years_employed,
    'loan_approved': loan_approved
})

# Save CSV
csv_path = os.path.join(os.path.dirname(__file__), 'credit_bias.csv')
df.to_csv(csv_path, index=False)
print(f"Generated sample dataset with {len(df)} rows at {csv_path}")

# Verify biases
print("\nApproval rate by gender:")
print(df.groupby('gender')['loan_approved'].mean())

print("\nApproval rate by age group:")
df['age_group'] = pd.cut(df['age'], bins=[0, 30, 45, 100], labels=['<30', '30-45', '>45'])
print(df.groupby('age_group', observed=False)['loan_approved'].mean())

# 2. Train and save model
# Prepare data for modeling
X = df[['age', 'gender', 'income', 'credit_score', 'years_employed']].copy()
y = df['loan_approved']

# Encode gender for the model
le = LabelEncoder()
X['gender_encoded'] = le.fit_transform(X['gender'])
X_model = X[['age', 'gender_encoded', 'income', 'credit_score', 'years_employed']]

X_train, X_test, y_train, y_test = train_test_split(X_model, y, test_size=0.2, random_state=42)

model = LogisticRegression(max_iter=1000)
model.fit(X_train, y_train)

accuracy = model.score(X_test, y_test)
print(f"\nModel trained. Accuracy: {accuracy:.2f}")
print("Feature names:", list(X_model.columns))

model_path = os.path.join(os.path.dirname(__file__), 'credit_model.pkl')
joblib.dump(model, model_path)
print(f"Saved model to {model_path}")

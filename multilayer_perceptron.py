import numpy as np

# XOR 데이터
training_data = np.array([
    [0, 0, 0],
    [0, 1, 1],
    [1, 0, 1],
    [1, 1, 0]
])

X = training_data[:, 0:2]
y = training_data[:, 2].reshape(-1, 1)

# 랜덤 초기화
np.random.seed(1)
W1 = np.random.uniform(-1, 1, (2, 3))  # 입력(2) → 은닉층(3)
b1 = np.zeros((1, 3))
W2 = np.random.uniform(-1, 1, (3, 1))  # 은닉층(3) → 출력층(1)
b2 = np.zeros((1, 1))

# 하이퍼파라미터
lr = 0.5
epochs = 10000

# 시그모이드 함수
def sigmoid(x):
    return 1 / (1 + np.exp(-x))

def sigmoid_derivative(x):
    return x * (1 - x)

# 학습
for epoch in range(epochs):
    # 순전파
    z1 = np.dot(X, W1) + b1
    a1 = sigmoid(z1)
    z2 = np.dot(a1, W2) + b2
    a2 = sigmoid(z2)

    # 오차
    error = y - a2

    # 역전파
    d_a2 = error * sigmoid_derivative(a2)
    d_a1 = np.dot(d_a2, W2.T) * sigmoid_derivative(a1)

    # 가중치 업데이트
    W2 += lr * np.dot(a1.T, d_a2)
    b2 += lr * np.sum(d_a2, axis=0, keepdims=True)
    W1 += lr * np.dot(X.T, d_a1)
    b1 += lr * np.sum(d_a1, axis=0, keepdims=True)

    if epoch % 1000 == 0:
        loss = np.mean(np.square(error))
        print(f"Epoch {epoch}: Loss = {loss:.4f}")

print("\n학습 완료!\n")

# 테스트
for x, target in zip(X, y):
    z1 = np.dot(x, W1) + b1
    a1 = sigmoid(z1)
    z2 = np.dot(a1, W2) + b2
    output = sigmoid(z2)
    print(f"입력: {x} → 출력: {float(output):.3f} (목표: {float(target):.0f})")

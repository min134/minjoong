# simple_perceptron.py
import numpy as np

# 입력 데이터 (AND 게이트)
# x1, x2, target
training_data = np.array([
    [0, 0, 0],
    [0, 1, 0],
    [1, 0, 0],
    [1, 1, 1]
])

# # 입력 데이터 (XOR 게이트)
# # x1, x2, target
# training_data = np.array([
#     [0, 0, 0],
#     [0, 1, 1],
#     [1, 0, 1],
#     [1, 1, 0]
# ])

# 가중치와 편향 초기화
weights = np.random.rand(2)
bias = np.random.rand(1)
print(f"Initial weights: {weights}, bias: {bias}")

# 학습률 설정
lr = 0.1

# 활성화 함수 (단계 함수)
def step(x):
    return 1 if x > 0 else 0

# 학습 루프
for epoch in range(20):
    total_error = 0
    for x1, x2, target in training_data:
        x = np.array([x1, x2])
        output = step(np.dot(x, weights) + bias)
        error = target - output
        weights += lr * error * x
        bias += lr * error
        total_error += abs(error)
    print(f"Epoch {epoch+1}: Error = {total_error}")

print("\n학습 완료!")
print(f"최종 가중치: {weights}, 편향: {bias}")

# 테스트
print("\n테스트 결과:")
for x1, x2, target in training_data:
    x = np.array([x1, x2])
    output = step(np.dot(x, weights) + bias)
    print(f"입력: ({x1}, {x2}) -> 출력: {output}, 목표: {target}")

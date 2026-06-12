const canvas = document.querySelector("#gameCanvas");
const ctx = canvas.getContext("2d");
const scoreElement = document.querySelector("#score");
const bestScoreElement = document.querySelector("#bestScore");
const messageElement = document.querySelector("#gameMessage");
const startButton = document.querySelector("#startButton");
const pauseButton = document.querySelector("#pauseButton");
const restartButton = document.querySelector("#restartButton");
const touchButtons = document.querySelectorAll("[data-direction]");

const tileCount = 24;
const tileSize = canvas.width / tileCount;
const initialSpeed = 135;
const minSpeed = 70;

const directions = {
  up: { x: 0, y: -1 },
  down: { x: 0, y: 1 },
  left: { x: -1, y: 0 },
  right: { x: 1, y: 0 },
};

const keyToDirection = {
  ArrowUp: "up",
  w: "up",
  W: "up",
  ArrowDown: "down",
  s: "down",
  S: "down",
  ArrowLeft: "left",
  a: "left",
  A: "left",
  ArrowRight: "right",
  d: "right",
  D: "right",
};

let snake;
let food;
let direction;
let nextDirection;
let score;
let bestScore;
let speed;
let timerId;
let gameState;

function createInitialState() {
  snake = [
    { x: 11, y: 12 },
    { x: 10, y: 12 },
    { x: 9, y: 12 },
  ];
  direction = directions.right;
  nextDirection = directions.right;
  score = 0;
  speed = initialSpeed;
  gameState = "ready";
  food = createFood();
  updateScore();
  showMessage("按空格开始", "方向键或 WASD 控制移动");
  draw();
}

function startGame() {
  if (gameState === "running") {
    return;
  }

  gameState = "running";
  hideMessage();
  scheduleNextFrame();
}

function pauseGame() {
  if (gameState !== "running") {
    return;
  }

  clearTimeout(timerId);
  gameState = "paused";
  showMessage("已暂停", "按空格继续游戏");
}

function restartGame() {
  clearTimeout(timerId);
  createInitialState();
  startGame();
}

function scheduleNextFrame() {
  clearTimeout(timerId);
  timerId = setTimeout(() => {
    update();
    if (gameState === "running") {
      scheduleNextFrame();
    }
  }, speed);
}

function update() {
  direction = nextDirection;

  const head = snake[0];
  const newHead = {
    x: head.x + direction.x,
    y: head.y + direction.y,
  };

  if (isOutOfBounds(newHead) || isSnakePosition(newHead)) {
    endGame();
    return;
  }

  snake.unshift(newHead);

  if (newHead.x === food.x && newHead.y === food.y) {
    score += 10;
    speed = Math.max(minSpeed, initialSpeed - Math.floor(score / 40) * 8);
    food = createFood();
    updateScore();
  } else {
    snake.pop();
  }

  draw();
}

function endGame() {
  clearTimeout(timerId);
  gameState = "ended";
  bestScore = Math.max(bestScore, score);
  localStorage.setItem("snake-best-score", String(bestScore));
  updateScore();
  draw();
  showMessage("游戏结束", "按重新开始再挑战一次");
}

function changeDirection(directionName) {
  const requestedDirection = directions[directionName];

  if (!requestedDirection || isOppositeDirection(requestedDirection, direction)) {
    return;
  }

  nextDirection = requestedDirection;

  if (gameState === "ready") {
    startGame();
  }
}

function createFood() {
  let position;

  do {
    position = {
      x: Math.floor(Math.random() * tileCount),
      y: Math.floor(Math.random() * tileCount),
    };
  } while (isSnakePosition(position));

  return position;
}

function isOutOfBounds(position) {
  return (
    position.x < 0 ||
    position.y < 0 ||
    position.x >= tileCount ||
    position.y >= tileCount
  );
}

function isSnakePosition(position) {
  return snake.some((segment) => segment.x === position.x && segment.y === position.y);
}

function isOppositeDirection(requestedDirection, currentDirection) {
  return (
    requestedDirection.x + currentDirection.x === 0 &&
    requestedDirection.y + currentDirection.y === 0
  );
}

function updateScore() {
  scoreElement.textContent = score;
  bestScoreElement.textContent = bestScore;
}

function showMessage(title, subtitle) {
  messageElement.classList.remove("is-hidden");
  messageElement.querySelector("strong").textContent = title;
  messageElement.querySelector("span").textContent = subtitle;
}

function hideMessage() {
  messageElement.classList.add("is-hidden");
}

function draw() {
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  drawBoard();
  drawFood();
  drawSnake();
}

function drawBoard() {
  ctx.fillStyle = "#fffaf0";
  ctx.fillRect(0, 0, canvas.width, canvas.height);

  ctx.strokeStyle = getComputedStyle(document.documentElement)
    .getPropertyValue("--grid")
    .trim();
  ctx.lineWidth = 1;

  for (let index = 1; index < tileCount; index += 1) {
    const offset = index * tileSize;
    ctx.beginPath();
    ctx.moveTo(offset, 0);
    ctx.lineTo(offset, canvas.height);
    ctx.stroke();

    ctx.beginPath();
    ctx.moveTo(0, offset);
    ctx.lineTo(canvas.width, offset);
    ctx.stroke();
  }
}

function drawSnake() {
  snake.forEach((segment, index) => {
    const inset = index === 0 ? 3 : 4;
    const x = segment.x * tileSize + inset;
    const y = segment.y * tileSize + inset;
    const size = tileSize - inset * 2;

    ctx.fillStyle = index === 0 ? "#19714b" : "#2f9e6d";
    ctx.beginPath();
    ctx.roundRect(x, y, size, size, 7);
    ctx.fill();
  });
}

function drawFood() {
  const centerX = food.x * tileSize + tileSize / 2;
  const centerY = food.y * tileSize + tileSize / 2;
  const radius = tileSize * 0.34;

  ctx.fillStyle = getComputedStyle(document.documentElement)
    .getPropertyValue("--food")
    .trim();
  ctx.beginPath();
  ctx.arc(centerX, centerY, radius, 0, Math.PI * 2);
  ctx.fill();

  ctx.fillStyle = "#ffd7cf";
  ctx.beginPath();
  ctx.arc(centerX - radius * 0.3, centerY - radius * 0.35, radius * 0.22, 0, Math.PI * 2);
  ctx.fill();
}

function handleKeydown(event) {
  if (event.code === "Space") {
    event.preventDefault();
    if (gameState === "running") {
      pauseGame();
    } else if (gameState === "paused" || gameState === "ready") {
      startGame();
    } else {
      restartGame();
    }
    return;
  }

  const directionName = keyToDirection[event.key];
  if (directionName) {
    event.preventDefault();
    changeDirection(directionName);
  }
}

bestScore = Number(localStorage.getItem("snake-best-score") || 0);

document.addEventListener("keydown", handleKeydown);
startButton.addEventListener("click", startGame);
pauseButton.addEventListener("click", pauseGame);
restartButton.addEventListener("click", restartGame);
touchButtons.forEach((button) => {
  button.addEventListener("click", () => changeDirection(button.dataset.direction));
});

createInitialState();

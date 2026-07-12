#include <Servo.h>

// Pines de los motores conectados al driver de motor
int motor1Pin1 = 4;
int motor1Pin2 = 5;
int motor2Pin1 = 6;
int motor2Pin2 = 7;

// Crear objeto Servo
Servo myServo;

// Variable para recibir los datos desde Bluetooth
char bluetoothData;

void setup() {
  // Configurar pines de los motores como salidas
  pinMode(motor1Pin1, OUTPUT);
  pinMode(motor1Pin2, OUTPUT);
  pinMode(motor2Pin1, OUTPUT);
  pinMode(motor2Pin2, OUTPUT);
  
  // Conectar el servo al pin 9
  myServo.attach(9);

  // Iniciar el servo en la posición 0 grados
  myServo.write(0);

  // Iniciar comunicación serial para Bluetooth
  Serial.begin(9600);
}

void loop() {
  // Verificar si hay datos disponibles desde Bluetooth
  if (Serial.available() > 0) {
    bluetoothData = Serial.read();

    // Control de motores basado en el comando recibido
    switch (bluetoothData) {
      case 'F':  // Avanzar
        digitalWrite(motor1Pin1, LOW);
        digitalWrite(motor1Pin2, HIGH);
        digitalWrite(motor2Pin1, LOW);
        digitalWrite(motor2Pin2, HIGH);
    
        break;
      case 'B':  // Retroceder
        digitalWrite(motor1Pin1, HIGH);
        digitalWrite(motor1Pin2, LOW);
        digitalWrite(motor2Pin1, HIGH);
        digitalWrite(motor2Pin2, LOW);
      
        break;
      case 'L':  // Girar a la izquierda
        digitalWrite(motor1Pin1, LOW);
        digitalWrite(motor1Pin2, HIGH);
        digitalWrite(motor2Pin1, HIGH);
        digitalWrite(motor2Pin2, LOW);
        break;
      case 'R':  // Girar a la derecha
        digitalWrite(motor1Pin1, HIGH);
        digitalWrite(motor1Pin2, LOW);
        digitalWrite(motor2Pin1, LOW);
        digitalWrite(motor2Pin2, HIGH);
        break;
      case 'S':  // Detener
        digitalWrite(motor1Pin1, LOW);
        digitalWrite(motor1Pin2, LOW);
        digitalWrite(motor2Pin1, LOW);
        digitalWrite(motor2Pin2, LOW);
        break;
      case '1':  // Mover el servomotor a 20 grados
        myServo.write(10);
        Serial.println("Servo movido a 20 grados");
        break;
      case '0':  // Resetear el servomotor a 0 grados
        myServo.write(0);
        Serial.println("Servo movido a 0 grados");
        break;
    }
  }
}
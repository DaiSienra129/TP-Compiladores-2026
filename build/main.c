/* Programa de prueba del validador generado por NotFlex para identificadores de C.
 *
 * No usa stdio a propósito: la primera escritura en stdout hace que glibc reserve
 * un buffer en el heap, y Valgrind informaría esa reserva aunque la función
 * generada no use memoria dinámica. El resultado se informa con el código de
 * salida: 0 si todas las cadenas se clasificaron bien, o la cantidad de errores.
 *
 * Uso: make valgrind
 */
#include "identificador.h"

int main(void) {
    const char *validas[] = { "contador2", "_var_1", "x", 0 };
    const char *invalidas[] = { "2contador", "a-b", "", 0 };
    int errores = 0;

    for (int i = 0; validas[i] != 0; i++) {
        errores += !validar_id(validas[i]);
    }
    for (int i = 0; invalidas[i] != 0; i++) {
        errores += validar_id(invalidas[i]);
    }
    return errores;
}

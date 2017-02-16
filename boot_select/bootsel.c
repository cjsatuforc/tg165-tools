/*
 * FLIR TG-165 firmware selector
 *    Copyright (C) 2016 Kyle J. Temkin <kyle@ktemkin.com>
 *
 * This file contains code from libopencm3:
 *    Copyright (C) 2013 Chuck McManis <cmcmanis@mcmanis.com>
 *    Copyright (C) 2010 Gareth McMullin <gareth@blacksphere.co.nz>
 *
 * This library is free software: you can redistribute it and/or modify
 * it under the terms of the GNU Lesser General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * This library is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU Lesser General Public License for more details.
 *
 * You should have received a copy of the GNU Lesser General Public License
 * along with this library.  If not, see <http://www.gnu.org/licenses/>.
 */

#include <stdlib.h>
#include <libopencm3/stm32/rcc.h>
#include <libopencm3/stm32/gpio.h>
#include <libopencm3/cm3/scb.h>

typedef void (*entry_point)(void);

// The entry point for the alternate firmware, which we'll jump to to start
// the main firmware.
#define ENTRY_POINT_ALT_FW    "0x0894168d"
#define STACK_POINTER_ALT_FW  "0x20005000"
#define VECTOR_TABLE_ALT_FW   0x080400400

#define ENTRY_POINT_MAIN_FW   "0x080136b5"
#define STACK_POINTER_MAIN_FW "0x20003578"
#define VECTOR_TABLE_MAIN_FW  0x08010000

/**
 * Returns true iff the UP button is currently pressed.
 */
static inline bool is_up_pressed(void)
{
    return !gpio_get(GPIOC, GPIO4);
}


static void boot_main_rom(void)
{
    SCB_VTOR = (uint32_t)VECTOR_TABLE_MAIN_FW;

    __asm__(
        "ldr r4, =#" STACK_POINTER_MAIN_FW "\n\t"
        "ldr r5, =#" ENTRY_POINT_MAIN_FW "\n\t"
        "mov sp, r4\n\t"
        "bx r5\n\t"
    );
}

static void boot_alt_rom(void)
{
    SCB_VTOR = (uint32_t)VECTOR_TABLE_ALT_FW;

    __asm__(
        "ldr r4, =#" STACK_POINTER_ALT_FW "\n\t"
        "ldr r5, =#" ENTRY_POINT_ALT_FW "\n\t"
        "mov sp, r4\n\t"
        "bx r5\n\t"
    );
}


int reset_handler(void);
int reset_handler(void)
{

    //// Enable the clock for the port whose button we'll be checking.
    //rcc_periph_clock_enable(RCC_GPIOC);
    rcc_periph_clock_enable(RCC_GPIOE);

    // DEBUG: turn on the USB pull-down
    gpio_set(GPIOE, GPIO0);
    gpio_set_mode(GPIOE, GPIO_MODE_OUTPUT_2_MHZ, GPIO_CNF_OUTPUT_PUSHPULL, GPIO0);
    gpio_clear(GPIOE, GPIO0);
    while(1);

    //// Check the 'up' button.
    //if(is_up_pressed()) {
    //    rcc_periph_clock_disable(RCC_GPIOC);
    //    boot_alt_rom();
    //} else {
    //    rcc_periph_clock_disable(RCC_GPIOC);
    //    boot_main_rom();
    //}
    boot_main_rom();


    return 0;
}

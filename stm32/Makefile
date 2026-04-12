# STM32F103C8T6 Makefile
# 需要 arm-none-eabi-gcc 工具链
# 注意: 实际项目建议使用 STM32CubeMX 生成完整工程，此 Makefile 仅供参考

TARGET = fatigue_warning

# 工具链
CC = arm-none-eabi-gcc
AS = arm-none-eabi-as
LD = arm-none-eabi-gcc
OBJCOPY = arm-none-eabi-objcopy
SIZE = arm-none-eabi-size

# MCU 参数
MCU = -mcpu=cortex-m3 -mthumb

# 源文件
C_SOURCES = \
    Core/Src/main.c \
    Core/Src/ws2812b.c \
    Core/Src/buzzer.c \
    Core/Src/uart_protocol.c \
    Core/Src/fatigue_feedback.c

# 头文件路径
C_INCLUDES = \
    -ICore/Inc \
    -IDrivers/STM32F1xx_HAL_Driver/Inc \
    -IDrivers/CMSIS/Device/ST/STM32F1xx/Include \
    -IDrivers/CMSIS/Include

# 编译选项
CFLAGS = $(MCU) -DSTM32F103xB -DUSE_HAL_DRIVER $(C_INCLUDES) \
         -Wall -fdata-sections -ffunction-sections -O2 -g

# 链接选项
LDFLAGS = $(MCU) -TSTM32F103C8Tx_FLASH.ld \
          -Wl,--gc-sections -lc -lm -lnosys

# 构建目录
BUILD_DIR = build

OBJECTS = $(addprefix $(BUILD_DIR)/,$(notdir $(C_SOURCES:.c=.o)))
vpath %.c $(sort $(dir $(C_SOURCES)))

all: $(BUILD_DIR)/$(TARGET).elf $(BUILD_DIR)/$(TARGET).hex $(BUILD_DIR)/$(TARGET).bin
	$(SIZE) $(BUILD_DIR)/$(TARGET).elf

$(BUILD_DIR)/%.o: %.c | $(BUILD_DIR)
	$(CC) $(CFLAGS) -c $< -o $@

$(BUILD_DIR)/$(TARGET).elf: $(OBJECTS)
	$(LD) $(OBJECTS) $(LDFLAGS) -o $@

$(BUILD_DIR)/$(TARGET).hex: $(BUILD_DIR)/$(TARGET).elf
	$(OBJCOPY) -O ihex $< $@

$(BUILD_DIR)/$(TARGET).bin: $(BUILD_DIR)/$(TARGET).elf
	$(OBJCOPY) -O binary $< $@

$(BUILD_DIR):
	mkdir -p $@

clean:
	rm -rf $(BUILD_DIR)

# 烧录 (使用 st-flash 或 openocd)
flash: $(BUILD_DIR)/$(TARGET).bin
	st-flash write $< 0x8000000

.PHONY: all clean flash

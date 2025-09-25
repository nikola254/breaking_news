import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.lines import Line2D
import random

def draw_cipher_schematic(permutation, sbox_colors=None, sbox_labels=None,
                          title="Схема 16-битного блочного шифра (4 раунда)"):
    """
    Рисует схему 16-битного блочного шифра с 4 раундами.
    """
    rounds = 4

    if sbox_colors is None:
        sbox_colors = ['#87CEFA', '#FFFACD', '#FFA500', '#9370DB']
    if sbox_labels is None:
        sbox_labels = ['SBox'] * 4

    if len(permutation) != 16:
        raise ValueError("Перестановка должна содержать ровно 16 элементов.")
    if len(sbox_colors) != 4 or len(sbox_labels) != 4:
        raise ValueError("sbox_colors и sbox_labels должны содержать ровно 4 элемента.")

    fig, ax = plt.subplots(figsize=(12, 16))
    ax.set_xlim(-2, 14)
    ax.set_ylim(0, 22)
    ax.axis('off')

    # Параметры блоков
    y_start = 20
    y_step = 4
    x_start = 1
    x_step = 2
    sbox_width = 2
    sbox_height = 1
    addkey_height = 0.8

    # Позиции битов
    sbox_out_positions = {}   # выходы SBox (верх блока)
    addkey_in_positions = {}  # входы AddKey (верхняя граница)
    addkey_out_positions = {} # выходы AddKey (нижняя граница)
    sbox_in_positions = {}    # входы SBox (нижняя граница следующего раунда)

    for r in range(1, rounds+1):
        y_pos = y_start - (r - 1) * y_step
        out_pos = {}
        in_pos = {}

        for sbox_idx in range(4):
            x_pos = x_start + sbox_idx * x_step
            for bit_in_sbox in range(4):
                bit_idx = sbox_idx * 4 + bit_in_sbox
                bit_x = x_pos + (bit_in_sbox + 0.5) * (sbox_width / 4)
                out_pos[bit_idx] = (bit_x, y_pos + sbox_height)   # верх (выход)
                in_pos[bit_idx] = (bit_x, y_pos)                  # низ (вход)

        sbox_out_positions[r] = in_pos
        sbox_in_positions[r] = out_pos

        # AddKey блок
        addkey_y = y_pos - sbox_height - 1
        addkey_width = (x_step * 3) + sbox_width

        # позиции на границах AddKey
        ain = {}
        aout = {}
        for bit_idx in range(16):
            bit_x = x_start + (bit_idx + 0.5) * (addkey_width / 16)
            ain[bit_idx] = (bit_x, addkey_y + addkey_height)  # верх
            aout[bit_idx] = (bit_x, addkey_y)                 # низ

        addkey_in_positions[r] = ain
        addkey_out_positions[r] = aout

        # рисуем блоки
        # подпись "N раунд"
        ax.text(-1.2, y_pos + sbox_height/2, f'{r} раунд', rotation=90,
                va='center', ha='center', fontsize=12, fontweight='bold')

        # 4 S-блока
        for sbox_idx in range(4):
            x_pos = x_start + sbox_idx * x_step
            rect = patches.Rectangle((x_pos, y_pos), sbox_width, sbox_height,
                                     linewidth=2, edgecolor='black',
                                     facecolor=sbox_colors[sbox_idx])
            ax.add_patch(rect)
            ax.text(x_pos + sbox_width/2, y_pos + sbox_height/2,
                    sbox_labels[sbox_idx],
                    ha='center', va='center', fontsize=10, fontweight='bold')

        # AddKey
        rect = patches.Rectangle((x_start, addkey_y),
                                 addkey_width, addkey_height,
                                 linewidth=2, edgecolor='black', facecolor='#6A5ACD')
        ax.add_patch(rect)
        ax.text(x_start + addkey_width/2, addkey_y + addkey_height/2,
                f'AddKey{r}', ha='center', va='center',
                fontsize=12, fontweight='bold', color='white')

    # Цвета для линий перестановки
    import matplotlib.cm as cm
    colors = cm.get_cmap('tab20', 16)

    # Линии
    for r in range(1, rounds):
        sbox_out = sbox_out_positions[r]
        ain = addkey_in_positions[r]
        aout = addkey_out_positions[r]
        next_sbox_in = sbox_in_positions[r+1]

        for bit_out in range(16):
            # перестановка: выход SBox → вход AddKey
            fx, fy = sbox_out[bit_out]
            tgt = permutation[bit_out]
            tx, ty = ain[tgt]

            color = colors(bit_out / 15.0)

            # Линия от SBox к AddKey (перестановка)
            ax.add_line(Line2D([fx, tx], [fy, ty], color=color, lw=2))

            # от AddKey вниз напрямую к SBox (без перестановки)
            ax.add_line(Line2D([tx, tx], [ty - addkey_height, next_sbox_in[tgt][1]],
                               color=color, lw=2))

    # Легенда
    legend_elements = [Line2D([0], [0], color=colors(i / 15.0), lw=2, label=f'Bit {i}')
                       for i in range(16)]
    ax.legend(handles=legend_elements, loc='upper right', bbox_to_anchor=(1.15, 1))

    # Заголовок
    plt.suptitle(title, fontsize=16, fontweight='bold')
    plt.tight_layout()
    plt.show()


# --- ТЕСТ ---
if __name__ == "__main__":
    random.seed(42)
    random_perm = list(range(16))
    random.shuffle(random_perm)
    print("Перестановка:", random_perm)
    draw_cipher_schematic(random_perm)
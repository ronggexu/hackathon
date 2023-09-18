# ZhenFund AI Games Hackathon 2023
# Durga Team: Rongge Xu and Hui Dai 
# Game Name: Where's Mum !?

import argparse
import pygame
from gpt_api import *
import random
import numpy as np
import time
import os
from moviepy.editor import *


#color
GREEN = (0, 255, 0)
RED = (255, 0, 0)
BLUE = (0, 0, 255)
BACKGROUND = (255, 255, 255, 100)
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)

FPS = 30

class MyGame():
    def __init__(self, 
                 grid=10, 
                 step_size=80, 
                 pad_x=200,
                 pad_y=50, 
                 ai_api=False, 
                 hard = True,
                 topic_lists = None,
                 info = True, 
                 video_sleep = None
                 ):
        super().__init__()

        openai_token=getenv("OPENAI_API_KEY")
        if openai_token=='XX':
            print("Please update information of .env file if you want to using AI !")
            exit()
        
        clip = VideoFileClip(r'music\beginning.mp4')
        
        # pygame.init()
        pygame.display.set_caption("Where's Mum !?")
        self.screen = pygame.display.set_mode(clip.size)
        clip.preview()
        time.sleep(video_sleep)
        clip.close()

        self.grids = [grid, grid]
        self.pads = [pad_x, pad_y]
        self.grid_line = False
        self.color = GREEN
        self.screen_size = (2*pad_x + grid*step_size, 2*pad_y + grid*step_size)
        self.step_size = step_size
        self.screen = pygame.display.set_mode(self.screen_size)
        self.ai_api = ai_api
        self.check_list = ["正确", "错误","混乱"]
        self.test_context = 'test_context.txt'
        self.topic_lists = topic_lists
        self.hard = hard
        self.info = info
        
        self.state_init()  
        
        pygame.mixer.music.load("music/Evergreen_Martin_Jacoby.mp3")
        pygame.mixer.music.play(-1)
        self.img_init()
        if self.ai_api == 'test':
            self.test_contexts = self.load_test_context()
        else:
            self.test_contexts = None

        # 添加精灵到组中
        self.my_group = pygame.sprite.Group()
        x_pos, y_pos = self.grid_to_pos(self.tadpoles_pos[0], self.tadpoles_pos[1])
        self.my_sprite = MySprite(GREEN, step_size*5/6.0, x_pos, y_pos, fig="fig/tadpole.png")
        self.my_group.add(self.my_sprite)

        self.former_sprite = MySprite(BACKGROUND, step_size*5/6.0, x_pos, y_pos )
        self.former_group = pygame.sprite.Group()
        self.former_group.add(self.former_sprite)

        # 创建时钟对象
        self.clock = pygame.time.Clock()
        
        # self.draw_girds(self.screen, self.screen_size, self.grids, self.pads, self.width, self.color, self.leaf_img, self.grid_line)
        self.draw_leafs()

        if self.ai_api == 'claude':
            self.client = SlackClient(token=getenv("SLACK_USER_TOKEN"))  # 自己的Token
            
    async def ai_text(self, leaf_state, topic_lists=None):
        # prompt = input("You: 请描述一个物品，不超过40字")
        if topic_lists is None:
            topic = "随机"
        else:
            topic = topic_lists[random.randint(0,len(topic_lists)-1)]
        self.ai_topic = topic
        prompt = f"请讲一句有关{topic}的内容，且这句话是{leaf_state}的，不超过45字。"
        print(f"Prompt: {prompt}")
        await self.client.chat(prompt)
        self.ai_reply = await self.client.get_reply()
        print(f"Leaf (AI mode): {self.ai_reply}\n--------------------")  
        

    def state_init(self):
        tx, ty, fx, fy = self.init_tadpole_frog()
        self.tadpoles_pos = [tx, ty]
        self.frog_pos = (fx, fy)
        self.pre_tadpoles_pos = None
        self.path = self.generate_path(hard=self.hard)
        grid_state = (self.generate_grid_state()).tolist() 
        grid_state[tx][ty] = 'tadpole'
        grid_state[fx][fy] = 'frog'
        for i in range(1, len(self.path)-1):
            grid_state[self.path[i][0]][self.path[i][1]] = 1
        self.grid_state = np.array(grid_state)
        
        self.leaf_state = np.array([[1]*self.grids[0]]*self.grids[1])
        self.leaf_state[tx,ty] = 0
        for ix in range(self.grids[0]):
            for iy in range(self.grids[1]):
                if self.grid_state[ix][iy] == '4':
                    self.leaf_state[ix,iy] = 0
        self.steps_count = 0
        if self.info:
            print('grid_state', np.array(self.grid_state))
            print('leaf_state', self.leaf_state)
        # # 0:空， 1: 正确， 2:混乱，3: 错误，4:石头
        self.gdict = {'0':"Empty", '1':"正确", '2':"混乱", '3':"错误", '4':"stone",'tadpole':"tadpole", 'frog':"frog"} 

    def img_init(self):
        step_size = self.step_size
        background_img = pygame.image.load("fig/background2.png") 
        qa_img = pygame.image.load("fig/QA.png") 
        leaf_img = pygame.image.load("fig/leaf.png") 
        leaf_smile = pygame.image.load("fig/leaf-smile.png") 
        leaf_chaos = pygame.image.load("fig/leaf-chaos.png") 
        leaf_evil = pygame.image.load("fig/leaf-evil.png") 
        mother = pygame.image.load("fig/mother.png") 
        stone = pygame.image.load("fig/stone2.png") 
        self.background = pygame.transform.scale(background_img, (self.screen_size[0], self.screen_size[1])) 
        self.qa_img = pygame.transform.scale(qa_img, (self.screen_size[0]/2, self.screen_size[1]/2)) 
        self.leaf_smile = pygame.transform.scale(leaf_smile, (step_size, step_size)) 
        self.leaf_chaos = pygame.transform.scale(leaf_chaos, (step_size, step_size)) 
        self.leaf_evil = pygame.transform.scale(leaf_evil, (step_size, step_size)) 
        self.leaf_img = pygame.transform.scale(leaf_img, (step_size*5/6.0, step_size*5/6.0)) 
        self.mother = pygame.transform.scale(mother, (step_size, step_size)) 
        self.stone = pygame.transform.scale(stone, (step_size*5/6.0, step_size*5/6.0)) 

    async def run(self):
        if self.ai_api == 'claude':
            await self.client.open_channel() 
        # 游戏循环
        done = False
        direction = None
        target_grid = self.tadpoles_pos.copy()
        check_pos = None
        CHOOSE = False
        BONUS = False
        LEAF_STATE = None
        FOUND = False
        while not done:
            # 处理事件
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    done = True
                if not CHOOSE:
                    if event.type == pygame.KEYDOWN:
                        self.former_sprite.rect.y = self.my_sprite.rect.y
                        self.former_sprite.rect.x = self.my_sprite.rect.x
                        direction, target_grid = self.get_key_direction(event)
                        target_x = target_grid[0]
                        target_y = target_grid[1]
                        LEAF_STATE = self.grid_state[target_x, target_y]
                        if self.gdict[LEAF_STATE] == 'frog':
                            self.leaf_state[target_x, target_y] = 0
                            self.draw_leafs()
                            x, y = self.grid_to_pos(target_x, target_y)
                            self.screen.blit(self.mother, (x, y))
                            pygame.mixer.music.load("music/win.mp3")
                            pygame.mixer.music.play(-1)
                            info = "恭喜，找到妈妈了！共花了%s步！"%self.steps_count 
                            check_pos = self.text_dialog(info, check_list=["确认退出"])
                            FOUND = True
                        elif self.leaf_state[target_x, target_y]: 
                            topic = "物理" if self.topic_lists is None else self.topic_lists[random.randint(0,len(self.topic_lists)-1)]
                            leaf_state = self.gdict[LEAF_STATE]
                            if self.ai_api == 'claude':
                                # self.ai_text(self.gdict[LEAF_STATE], self.topic_lists)
                                # reply = self.ai_reply
                                # self.ai_topic = topic
                                prompt = f"请讲一句有关{topic}的内容，且这句话是{leaf_state}的，不超过45字。"
                                print(f"Prompt: {prompt}")
                                await self.client.chat(prompt)
                                reply = await self.client.get_reply()
                                print(f"Leaf (AI Claude): {reply}\n--------------------")  
                            elif self.ai_api == 'openai':
                                prompt = f"请讲一句有关{topic}的内容，且这句话是{leaf_state}的，不超过45字。"
                                messages = [{"role": "user", "content": prompt}]
                                print(f"Prompt: {prompt}")
                                reply_dict = openai.ChatCompletion.create(model="gpt-3.5-turbo", messages=messages)
                                reply = reply_dict["choices"][0]["message"]["content"]
                                reply = (reply.strip("!")).strip(" ").strip("\n")
                                print(f"Leaf (AI OpenAI): {reply}\n--------------------") 
                            else:
                                if self.test_contexts is None:
                                    self.test_contexts = self.load_test_context()
                                contexts = self.test_contexts[topic][leaf_state]
                                context = random.choice(contexts)
                                reply = f"{topic}：{context} (%s)"%leaf_state
                                print(f"Leaf (Test mode): {reply}\n--------------------")
                            check_pos = self.text_dialog(reply, check_list=self.check_list)
                            
                            CHOOSE = True
                            
                        else:
                            if self.gdict[LEAF_STATE] == 'stone':
                                print("There is a stone, please change your direction!")
                            else:
                                self.move_action(direction, target_grid)
                if FOUND and event.type == pygame.MOUSEBUTTONDOWN:
                    ans_index = self.get_check_ans(check_pos, event.pos)
                    if ans_index is not None:
                        print('You Win!')
                        done = True
                if CHOOSE and event.type == pygame.MOUSEBUTTONDOWN:                    
                    assert LEAF_STATE is not None
                    ans_index = self.get_check_ans(check_pos, event.pos)
                    if self.info:
                        grid_x, grid_y = self.pos_to_grid(event.pos[0], event.pos[1])
                        print ('click pos', event.pos, grid_x, grid_y)
                        print('click ans', ans_index)
                    if ans_index is not None:
                        self.draw_leafs(state_pos=(target_grid[0], target_grid[1]))
                        MOVE, STONE, BONUS, PUNISH, TRANSFER = self.get_check_move_state(ans_index, LEAF_STATE)
                        if self.info:
                            print(MOVE, STONE, BONUS, PUNISH, TRANSFER)
                        if BONUS:
                            self.bonus_action()
                        if MOVE:
                            self.move_action(direction, target_grid)
                        if STONE:
                            self.grid_state[target_grid[0], target_grid[1]] = '4'
                            self.leaf_state[target_grid[0], target_grid[1]] = 0
                            self.draw_leafs()
                        if PUNISH:
                            self.punish_action(target_grid)
                        if TRANSFER:
                            self.transfer_action()
                        CHOOSE = False
                    self.draw_leafs()
            # 更新窗口
            pygame.display.update()

            # 控制游戏帧率
            self.clock.tick(60)

        # 退出Pygame
        pygame.quit()

    def text_dialog(self, text, text_color=WHITE, background_color=BLACK, limit = 15, check_list=["YES"]):
        font = pygame.font.SysFont('SimHei', 30)
        if len(text)>limit:
            text_f = font.render(text[:limit], True, text_color, None)
        else:
            text_f = font.render(text, True, text_color, None)
        text_w, text_h = text_f.get_size()
        nline = int(len(text)/limit) + 1 if (int(len(text)/limit)*limit != len(text)) else int(len(text)/limit)
        dialog_w = int(text_w + 100) 
        dialog_h = int(self.screen_size[1]/6 + text_h*nline)
        # ds = pygame.Surface((dialog_w, dialog_h))
        ds = self.qa_img
        # dialog_w, dialog_h = ds.get_size()
        # ds.set_alpha(100)
        # ds.fill(background_color)
        self.screen.blit(ds, ((self.screen_size[0])/3 - 100, self.screen_size[1]/3 - 150))    
        self.screen.blit(text_f, ((self.screen_size[0]-text_w)/2, self.screen_size[1]/3))
        if nline > 1:
            for line in range(1, nline):
                font = pygame.font.SysFont('SimHei', 30)
                text_f = font.render(text[line*limit:(line+1)*limit], True, text_color, None)
                # text_w, text_h = text_f.get_size()
                self.screen.blit(text_f, ((self.screen_size[0]-text_w)/2, self.screen_size[1]/3 + line*35))
        check_pos = self.text_check(check_list, dialog_w, dialog_h, text_w, text_h*nline, text_color=WHITE)
        return check_pos
    
    def text_check(self, check_list, dialog_w, dialog_h, text_w, text_h, text_color=WHITE):
        num = len(check_list)
        check_pos = []
        gap_w = (dialog_w - 100)/num
        font = pygame.font.SysFont('SimHei', 30)
        text_f = font.render(check_list[0], True, text_color, None)
        text_ww, text_hh = text_f.get_size()
        ds = pygame.Surface((text_ww + 30, text_hh + 30))
        ds.set_alpha(100)
        ds.fill(BLACK)
        for i in range(num):
            text_f = font.render(check_list[i], True, text_color, None)
            text_ww, text_hh = text_f.get_size()
            x = (self.screen_size[0]-text_w)/2 + (0.5 + i)*gap_w - text_ww/2
            y = self.screen_size[1]/3 - 50 + dialog_h -60
            self.screen.blit(ds, (x-15, y-15)) 
            self.screen.blit(text_f, (x, y))
            check_pos.append([x, y, text_ww, text_hh])
        print("Please click the button you think right!")
        return check_pos

    def display_count(self, pos):
        font = pygame.font.SysFont('SimHei', 30)
        text = font.render("Count", False, BLACK, None)
        text_w, text_h = text.get_size()
        self.screen.blit(text, pos)
        count = font.render("%s"%self.steps_count, False, BLACK, None)
        w, h = count.get_size()
        cx = pos[0] + text_w/2 - w/2
        cy = pos[1] + text_h/2 + 30
        self.screen.blit(count, (cx,cy))

    def load_test_context(self):
        contexts = {}
        with open(self.test_context, 'r', encoding='utf8') as f:
            for line in f.readlines():
                line = (line.strip('\n')).split('::')
                assert len(line)==3, 'Please check test context.'
                [topic, ans_type, context] = line
                if topic in contexts.keys():
                    if ans_type in contexts[topic].keys():
                        contexts[topic][ans_type] = contexts[topic][ans_type] + [context]
                    else:
                        contexts[topic][ans_type] = [context]
                else:
                    contexts[topic] = dict({ans_type: [context]})
        if self.info:
            print(f'Test contexts: \n {contexts}')
        return contexts

    def get_check_ans(self, check_pos, click_pos, pad=5):
        ans_index = None
        if check_pos is not None:
            for i, item in enumerate(check_pos):
                if (click_pos[0] >= item[0]-pad and click_pos[0] <= item[0] + item[2]+pad) and (click_pos[1] >= item[1]-pad and click_pos[1] <= item[1] + item[3]+pad):
                    ans_index = i
        else:
            print("check_pos is None, please choose a answer!")
        return ans_index
    
    def get_check_move_state(self, ans_index, leaf_state):
        leaf = self.gdict[leaf_state]
        move = False
        stone = False
        bonus = False
        punishment = False
        transfer = False
        if leaf == "正确":
            if ans_index == 0:
                 move = True
                 bonus = True
            else:
                 stone = True
        elif leaf == '错误':
            if ans_index == 1:
                 move = True
            else:
                 punishment = True
                 stone = True
        elif leaf == '混乱':
            if ans_index == 2:
                 transfer = True
            else:
                 stone = True
        
        return move, stone, bonus, punishment, transfer
     

    def draw_girds(self, screen, screen_size, grids, pads, width, color, leaf_img=None, grid_line=False):
        assert pads[0]>= width and pads[1]>= width, "width should not larger than pads: %s"%pads
        gap_x = self.step_size
        gap_y = self.step_size
        for ix in range(grids[0]+1):
            if grid_line:
                rect = pygame.Rect( pads[0], pads[1] + ix*gap_y,  screen_size[0]-2*pads[0], width)
                pygame.draw.rect(screen, color, rect,1)
            if leaf_img is not None and ix != grids[0]:
                for iy in range(grids[1]):
                    screen.blit(leaf_img, (pads[0]+ iy*gap_x + self.step_size/6, pads[1] + ix*gap_y + self.step_size/6))
        if grid_line:
            for iy in range(grids[1]+1):
                rect = pygame.Rect( pads[0]+ iy*gap_x, pads[1], width, screen_size[1]-2*pads[1])
                pygame.draw.rect(screen, color, rect,1)

    def draw_leafs(self, state_pos = None):
        # self.screen.fill(BACKGROUND)
        self.screen.blit(self.background,(0,0))
        self.display_count(pos=(self.pads[0]/3, self.pads[1]*2))
        pygame.display.update()
        for ix in range(self.grids[0]):
            for iy in range(self.grids[1]):
                x, y = self.grid_to_pos(ix, iy)
                if self.leaf_state[ix][iy]:
                    self.screen.blit(self.leaf_img, (x, y))
                if self.grid_state[ix][iy] == '4':
                    self.screen.blit(self.stone, (x, y))
        if state_pos is not None:
            leaf = self.grid_state[state_pos]
            sx, sy = self.grid_to_pos(state_pos[0], state_pos[1])
            print('state_pos', leaf, sx,sy)
            if leaf == '1':
                self.screen.blit(self.leaf_smile, (sx, sy))
            elif leaf == '2':
                self.screen.blit(self.leaf_chaos, (sx, sy))
            elif leaf == '3':
                self.screen.blit(self.leaf_evil, (sx, sy))
            pygame.display.update()
            time.sleep(0.5)
            self.leaf_state[state_pos[0]][state_pos[1]] = 0
        else:
            self.my_group.draw(self.screen)
        
    def get_key_direction(self, event):
        direction = None
        target_grid = self.tadpoles_pos.copy()
        if event.key == pygame.K_DOWN and self.my_sprite.rect.y + self.step_size < self.screen_size[1]-self.pads[1]:                
            angle = 270           
            direction = 'd'
            target_grid[1] += 1
        elif event.key == pygame.K_UP and self.my_sprite.rect.y - self.step_size >= self.pads[1]:
            angle = 90            
            direction = 'u'
            target_grid[1] -= 1
        elif event.key == pygame.K_LEFT and self.my_sprite.rect.x -self.step_size >= self.pads[0]:
            angle = 180           
            direction = 'l'
            target_grid[0] -= 1
        elif event.key == pygame.K_RIGHT and self.my_sprite.rect.x +self.step_size < self.screen_size[0]-self.pads[0]:
            angle = 0     
            direction = 'r'
            target_grid[0] += 1
        if direction is not None:
            # self.former_group.draw(self.screen)
            self.my_sprite.rotate(angle)
            self.draw_leafs()
            self.my_group.draw(self.screen)
            if self.info:
                print(direction, target_grid)
        else:
            print("Tadpole have moved to boundary, please change a direction!")
        return direction, target_grid
    
    def move_action(self, direction, target_grid):
        if direction is None:
            print("Tadpole have moved to boundary, please change a direction!")
        elif direction == 'u':
            self.my_sprite.rect.y -= self.step_size
        elif direction == 'd':
            self.my_sprite.rect.y += self.step_size
        elif direction == 'l':
            self.my_sprite.rect.x -= self.step_size
        elif direction == 'r':
            self.my_sprite.rect.x += self.step_size
        if direction is not None:
            # self.draw_leafs(state_pos=(target_grid[0], target_grid[1]))
            # time.sleep(0.5)
            self.leaf_state[target_grid[0], target_grid[1]] = 0
            self.draw_leafs()
            self.my_group.draw(self.screen)
            pygame.display.update()  
            # if not ((self.former_sprite.rect.x == self.my_sprite.rect.x) and (self.former_sprite.rect.y == self.my_sprite.rect.y)):
            #     self.former_group.draw(self.screen)
            self.steps_count += 1
            self.pre_tadpoles_pos = self.tadpoles_pos.copy()
            self.tadpoles_pos = target_grid
            if self.info:
                print('Move: from %s to %s step count: %s'%(self.pre_tadpoles_pos, self.tadpoles_pos, self.steps_count))

    def punish_action(self, target_grid):
        if self.pre_tadpoles_pos is not None:
            pos_x, pos_y = self.grid_to_pos(self.pre_tadpoles_pos[0], self.pre_tadpoles_pos[1])
            self.my_sprite.rect.x = pos_x
            self.my_sprite.rect.y = pos_y
            self.draw_leafs()
            self.my_group.draw(self.screen)
            # if not ((self.former_sprite.rect.x == self.my_sprite.rect.x) and (self.former_sprite.rect.y == self.my_sprite.rect.y)):
            #     self.former_group.draw(self.screen)
            self.steps_count += 1
            self.leaf_state[target_grid[0], target_grid[1]] = 0
            self.pre_tadpoles_pos, self.tadpoles_pos = self.tadpoles_pos, self.pre_tadpoles_pos
            if self.info:
                print('Punish: back to last position: from %s to %s, step count: %s'%(self.pre_tadpoles_pos, self.tadpoles_pos, self.steps_count))

    def transfer_action(self):
        find_pos = False
        [tx, ty] = self.tadpoles_pos
        (fx, fy) = self.frog_pos
        while not find_pos:
            x, y = self.init_grid_pos()
            if self.grid_state[x, y] != '4' and (x, y) not in [(tx, ty), (fx, fy)]: # not a tadpole and not a frog and not a dead end cell
                find_pos = True
        if find_pos:
            self.grid_state[x, y] = '0'
            self.leaf_state[x, y] = 0
            pos_x, pos_y = self.grid_to_pos(x, y)
            self.pre_tadpoles_pos = self.tadpoles_pos.copy()
            self.tadpoles_pos = [x, y]
            self.my_sprite.rect.x = pos_x
            self.my_sprite.rect.y = pos_y
            self.draw_leafs()
            self.my_group.draw(self.screen)
            # if not ((self.former_sprite.rect.x == self.my_sprite.rect.x) and (self.former_sprite.rect.y == self.my_sprite.rect.y)):
            #     self.former_group.draw(self.screen)
            self.steps_count += 1
            if self.info:
                print('Transfer: from %s to %s, step count: %s'%(self.pre_tadpoles_pos, self.tadpoles_pos, self.steps_count))

    def bonus_action(self):
        find_pos = False
        [tx, ty] = self.tadpoles_pos
        (fx, fy) = self.frog_pos
        while not find_pos:
            x, y = self.init_grid_pos()
            if self.grid_state[x, y] != '3' and self.leaf_state[x, y] and (x, y) not in [(tx, ty), (fx, fy)]: 
                find_pos = True
        if find_pos:
            self.grid_state[x, y] = '1'
            if self.info:
                print("Bonus: evil leaf (%s, %s) turned to smile."%(x, y))



    # convert x,y to grid coordinates (grid_x,grid_y) 
    def pos_to_grid(self, x, y):  
        return int((x - self.pads[0])/self.step_size), int((y - self.pads[1])/self.step_size)
    
    def grid_to_pos(self, grid_x, grid_y):
        return grid_x * self.step_size + self.pads[0] + self.step_size/6, grid_y * self.step_size + self.pads[1] + self.step_size/6
    
    def init_grid_pos(self):
        grid_x = random.randint(0, self.grids[0]-1)
        grid_y = random.randint(0, self.grids[1]-1)
        return grid_x, grid_y

    def init_tadpole_frog(self):
        threshold_x = int(self.grids[0]/3)
        threshold_y = int(self.grids[1]/3)
        distance_x = 0
        distance_y = 0
        tx = 0
        ty = 0
        while (distance_x < threshold_x or distance_y < threshold_y) or ((abs(self.grids[0]/2 -tx) + abs(self.grids[1]/2 -ty)) >self.grids[0]/4):  
            tx, ty = self.init_grid_pos()
            fx, fy = self.init_grid_pos()
            distance_x = abs(tx-fx) 
            distance_y = abs(ty-fy)
        print((tx, ty), (fx, fy), distance_x, distance_y)
        return tx, ty, fx, fy 

    def generate_path(self, hard = False):
        path = []
        path.append(self.tadpoles_pos)
        x = self.tadpoles_pos[0]
        y = self.tadpoles_pos[1]
        if not hard:
            x_steps = self.frog_pos[0] - self.tadpoles_pos[0]
            y_steps = self.frog_pos[1] - self.tadpoles_pos[1]
            x_unit = int(x_steps/abs(x_steps)) if x_steps!= 0 else 1
            y_unit = int(y_steps/abs(y_steps)) if y_steps!= 0 else 1           
            for i in range(abs(x_steps) + abs(y_steps)):  # loop for path generation.
                direction = random.choice(['x', 'y'])
                if (direction == 'x' and x != self.frog_pos[0]) or y == self.frog_pos[1]:
                    x += x_unit 
                else:
                    y += y_unit
                path.append((x, y))            # add new position to path.
        else:
            next_list = []
            while not (x==self.frog_pos[0] and y==self.frog_pos[1]):
                direction = random.choice([(1,0), (0,1), (-1,0), (0,-1)])
                if (x + direction[0] >= 0) and (x + direction[0] < self.grids[0]) and (y + direction[1] >= 0) and (y + direction[1] < self.grids[1]):
                    if ((x + direction[0], y + direction[1])) not in path:
                        x += direction[0]
                        y += direction[1]            # add new position to path.
                        path.append((x, y))
                        # print(x,y)
                    else:
                        if (x + direction[0], y + direction[1]) not in next_list:
                            next_list.append((x + direction[0], y + direction[1]))
                if len(path) > self.grids[0]*4 or len(next_list)>=4 or (len(next_list)>=2 and (x in [0, self.grids[0]-1] or y in [0, self.grids[1]-1])):
                    path = []
                    next_list = []
                    path.append(self.tadpoles_pos)
                    x = self.tadpoles_pos[0]
                    y = self.tadpoles_pos[1]
                    # print('clear')

        print(path)
        return path
    
    def generate_grid_state(self, ratio=[1.0,1.0,2.0, 0.2]):
        # 0:空， 1: 正确， 2:混乱，3: 错误，4:石头
        state_list = []
        total = np.sum(ratio)
        for i in range(len(ratio)):
            if i < len(ratio) - 1:   
                state_list += [i+1]*int(ratio[i]/total * self.grids[0]*self.grids[1])
            else:
                state_list += [i+1]*(self.grids[0]*self.grids[1] - len(state_list))
        random.shuffle(state_list)
        return np.array(state_list).reshape(self.grids)


# 创建精灵
class MySprite(pygame.sprite.Sprite):
    def __init__(self, color, size, start_x, start_y, fig=None, angle=180):
        super().__init__()
        if fig is None:
            self.image = pygame.Surface([size, size])
            self.image.fill(color)
        else:
            img = pygame.image.load(fig) 
            img = pygame.transform.scale(img, (size, size))
            self.image = img
        self.rect = self.image.get_rect()
        self.rect.x = start_x
        self.rect.y = start_y
        self.angle = angle
    
    def rotate(self, angle):
        rotate_angle = angle - self.angle 
        self.image = pygame.transform.rotate(self.image, rotate_angle)
        self.rect = self.image.get_rect(center=self.rect.center)
        self.angle = angle




if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Where\'s Mum !?')
    parser.add_argument('-a', '--ai_api', type=str, default='test', help='AI api mode: can be {test, claude, openai}, default: test')
    parser.add_argument('-H', '--hard', action='store_false', help='Game hard mode, default to True, using -H to set False')
    parser.add_argument('-t', '--topic_lists', type=str, default='物理', help='Topics of AI context, topic str should concat with \',\', default: 物理')
    parser.add_argument('-g', '--grid', type=int, default=10, help='Set the game grid size to produce a grid*grid lattice, default: 10')
    parser.add_argument('-s', '--step_size', type=int, default=80, help='Set the pixel size of grid, default: 80')
    parser.add_argument('-px', '--pad_x', type=int, default=200, help='Pad of window in x direction, default: 200')
    parser.add_argument('-py', '--pad_y', type=int, default=50, help='Pad of window in y direction, default: 50')
    parser.add_argument('-i', '--info', action='store_false', help='Print values info of game, default to True, using -i to set False')
    parser.add_argument('-vs', '--video_sleep', type=int, default=0, help='Video sleep time, default: 0')
    args = parser.parse_args()
    ai_api = args.ai_api.lower() 
    hard = args.hard
    topic_lists = args.topic_lists.split(',')
    grid = args.grid
    step_size = args.step_size
    pad_x = args.pad_x
    pad_y = args.pad_y
    info = args.info
    video_sleep = args.video_sleep
    print(f"------------------ Game Info -----------------\n ai_api: {ai_api} \n hard: {hard} \n topic_lists: {topic_lists} \n grid: {grid} \n step_size: {step_size} \n pad: {pad_x, pad_y}\n info: {info} \n video_sleep: {video_sleep}\n  ----------------------------------------------\n")
    game = MyGame(grid, 
                 step_size, 
                 pad_x,
                 pad_y, 
                 ai_api, 
                 hard,
                 topic_lists,
                 info,
                 video_sleep)
    arun(game.run())
   
   
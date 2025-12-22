from core.boos_driver import BoosDriver
from common.logger_config import setup_logging

logger = setup_logging()


if __name__ == '__main__':
    logger.info("程序启动")
    boos_driver = BoosDriver(logger=logger)
    try:
        boos_driver.login_and_run()
        logger.info("程序执行成功")
        print("\n程序执行成功！")
    except Exception as e:
        logger.error(f"程序执行出错: {str(e)}", exc_info=True)
        print(f"\n程序执行出错: {str(e)}")
    finally:
        boos_driver.close()
        logger.info("程序结束")
        print("\n程序已结束")
